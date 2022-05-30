
import logging
logger = logging.getLogger(__name__)

import re

from pylatexenc.latexnodes import ParsedArgumentsInfo
import pylatexenc.latexnodes.nodes as latexnodes_nodes
from pylatexenc.macrospec import (
    MacroSpec,
    LatexEnvironmentBodyContentsParser,
    ParsingStateDeltaExtendLatexContextDb,
)

from .llmspecinfo import LLMSpecInfo
from .llmenvironment import (
    LLMParsingStateDeltaSetBlockLevel,
    make_arg_spec,
)

from . import fmthelpers


_count_initials_formatters = {
    'a': fmthelpers.alphacounter,
    'A': fmthelpers.Alphacounter,
    'i': fmthelpers.romancounter,
    'I': fmthelpers.Romancounter,
    '1': str,
}
_rx_count_initial = re.compile(r'[aA1iI]')
def _get_counter_formatter_from_tag_template(tag_template):
    m = _rx_count_initial.search(tag_template)
    if m is not None:
        # substitute a counter
        left = tag_template[:m.start()]
        right = tag_template[m.end():]
        counter_formatter = _count_initials_formatters[m.group()]
        return lambda n: (left + counter_formatter(n) + right)

    # no counter. E.g., a bullet symbol
    return tag_template


class Enumeration(LLMSpecInfo):

    is_block_level = True

    body_parsing_state_delta = LLMParsingStateDeltaSetBlockLevel(is_block_level=True)

    def __init__(self, counter_formatter='•', annotations=None):
        super().__init__()
        self.counter_formatter = counter_formatter
        self.annotations = annotations
        
    def make_body_parser(self, token, nodeargd, arg_parsing_state_delta):
        return LatexEnvironmentBodyContentsParser(
            environmentname=token.arg,
            contents_parsing_state_delta=ParsingStateDeltaExtendLatexContextDb(
                extend_latex_context=dict(
                    macros=[
                        MacroSpec('item', arguments_spec_list=[
                            make_arg_spec('[', argname='custom_tag'),
                        ])
                    ]
                )
            )
        )

    def finalize_parsed_node(self, node):
        # parse the node structure right away when finializing then ode
        logger.debug("finalizing node: node = %r", node)
        item_nodelists = node.nodelist.split_at_node(
            lambda n: (n.isNodeType(latexnodes_nodes.LatexMacroNode)
                       and n.macroname == 'item'),
            keep_separators=True,
        )
        enumeration_items = []
        for j, item_nodelist in enumerate(item_nodelists):
            if not item_nodelist:
                continue # ?
            item_macro = item_nodelist[0]
            if item_macro is None:
                continue # ?
            if (j == 0
                and item_macro.isNodeType(latexnodes_nodes.LatexCharsNode)
                and item_macro.chars.strip() == ''):
                # skip leading whitespace
                continue
            if (not item_macro.isNodeType(latexnodes_nodes.LatexMacroNode)
                or item_macro.macroname != 'item'):
                raise LatexWalkerParseError(
                    msg=f"Expected ‘\\item’ in enumeration environment: {item_macro!r}",
                    pos=item_macro.pos,
                )
            item_content_nodelist = item_macro.latex_walker.make_nodelist(
                item_nodelist[1:],
                parsing_state=item_macro.parsing_state,
            )
            logger.debug("item_content_nodelist = %r  (blocks = %r)",
                         item_content_nodelist,
                         getattr(item_content_nodelist, 'llm_blocks', None))
            
            enumeration_items.append(
                (item_macro, item_content_nodelist)
            )

        node.enumeration_items = enumeration_items
        return node

    def render(self, node, render_context):

        fragment_renderer = render_context.fragment_renderer

        node_args = ParsedArgumentsInfo(node=node).get_all_arguments_info(
            ('tag_template',),
        )

        counter_formatter = self.counter_formatter

        if 'tag_template' in node_args and node_args['tag_template'].was_provided():
            tag_template_chars = node_args['tag_template'].get_content_as_chars()

            counter_formatter = _get_counter_formatter_from_tag_template(tag_template_chars)

        items_custom_tags = {}
        items_nodelists = []
        for j, iteminfo in enumerate(node.enumeration_items):
            item_macro, item_content_nodelist = iteminfo
            items_nodelists.append( item_content_nodelist )

            item_node_args = ParsedArgumentsInfo(node=item_macro).get_all_arguments_info(
                ('custom_tag',),
            )

            if 'custom_tag' in item_node_args and item_node_args['custom_tag'].was_provided():
                items_custom_tags[1+j] = item_node_args['custom_tag'].get_content_nodelist()

        def the_counter_formatter(n):
            if n in items_custom_tags:
                return items_custom_tags[n]
            if callable(counter_formatter):
                return counter_formatter(n)
            return counter_formatter

        return fragment_renderer.render_enumeration(
            items_nodelists,
            the_counter_formatter,
            render_context=render_context,
            annotations=self.annotations
        )