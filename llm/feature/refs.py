import logging
logger = logging.getLogger(__name__)

from pylatexenc.latexnodes import parsers as latexnodes_parsers
from pylatexenc.latexnodes import (
    LatexWalkerParseError,
    ParsedArgumentsInfo
)
#from pylatexenc import macrospec

from ..llmfragment import LLMFragment
from ..llmspecinfo import LLMMacroSpecBase
from ..llmenvironment import LLMArgumentSpec

from ._base import Feature



class RefInstance:
    def __init__(self, ref_type, ref_target, formatted_ref_llm_text, target_href):
        super().__init__()
        self.ref_type = ref_type
        self.ref_target = ref_target
        self.formatted_ref_llm_text = formatted_ref_llm_text
        self.target_href = target_href

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(ref_type={self.ref_type!r}, "
            f"ref_target={self.ref_target!r}, "
            f"formatted_ref_llm_text={self.formatted_ref_llm_text!r}, "
            f"target_href={self.target_href!r})"
        )


class FeatureRefsRenderManager(Feature.RenderManager):

    def initialize(self):
        self.ref_labels = {}
        
    def register_reference(self, ref_type, ref_target, formatted_ref_llm_text, target_href):
        r"""
        `formatted_ref_llm_text` is LLM code.
        """
        refinstance = RefInstance(
            ref_type=ref_type,
            ref_target=ref_target,
            formatted_ref_llm_text=formatted_ref_llm_text,
            target_href=target_href,
        )
        self.ref_labels[(ref_type, ref_target)] = refinstance
        logger.debug("Registered reference: %r", refinstance)

    def get_ref(self, ref_type, ref_target, *, resource_info):
        if (ref_type, ref_target) in self.ref_labels:
            return self.ref_labels[(ref_type, ref_target)]

        logger.debug(f"Couldn't find {(ref_type, ref_target)} in current document "
                     f"labels; will query external ref resolver.  {self.ref_labels=}")

        if self.feature.external_ref_resolver is not None:
            ref = self.feature.external_ref_resolver.get_ref(
                ref_type,
                ref_target,
                resource_info=resource_info,
            )
            if ref is not None:
                return ref

        raise ValueError(f"Ref target not found: ???{ref_type}:{ref_target}???")



class FeatureRefs(Feature):
    r"""
    Manager for internal references, such as ``\ref{...}``, ``\hyperref{...}``,
    etc.
    """

    feature_name = 'refs'
    RenderManager = FeatureRefsRenderManager

    def __init__(self, external_ref_resolver=None):
        super().__init__()
        # e.g., resolve a reference to a different code page in the EC zoo!
        self.external_ref_resolver = external_ref_resolver

    def set_external_ref_resolver(self, external_ref_resolver):
        if self.external_ref_resolver is not None:
            logger.warning("FeatureRefs.set_external_ref_resolver(): There is already "
                           "an external refs resolver set.  It will be replaced.")
        self.external_ref_resolver = external_ref_resolver

    def add_latex_context_definitions(self):
        return dict(
            macros=[
                RefMacro(macroname='ref', command_arguments=('ref_target',)),
                RefMacro(
                    macroname='hyperref',
                    command_arguments=('[]ref_target','display_text',)
                ),
            ]
        )


_ref_arg_specs = {
    'ref_target': LLMArgumentSpec(latexnodes_parsers.LatexCharsGroupParser(),
                                  argname='ref_target'),
    '[]ref_target': LLMArgumentSpec(
        latexnodes_parsers.LatexCharsGroupParser(
            delimiters=('[', ']'),
        ),
        argname='ref_target'
    ),
    'display_text': LLMArgumentSpec('{', argname='display_text',),
}


class RefMacro(LLMMacroSpecBase):

    delayed_render = True

    def __init__(
            self,
            macroname,
            *,
            ref_type='ref',
            command_arguments=('ref_target', 'display_text',)
    ):
        super().__init__(
            macroname=macroname,
            arguments_spec_list=self._get_arguments_spec_list(command_arguments),
        )
        self.ref_type = ref_type
        self.command_arguments = [ c.replace('[]','') for c in command_arguments ]
        
    @classmethod
    def _get_arguments_spec_list(self, command_arguments):
        return [ _ref_arg_specs[argname]
                 for argname in command_arguments ]

    def postprocess_parsed_node(self, node):

        node_args = ParsedArgumentsInfo(node=node).get_all_arguments_info(
            self.command_arguments,
        )

        ref_type = None
        ref_target = node_args['ref_target'].get_content_as_chars()
        if ':' in ref_target:
            ref_type, ref_target = ref_target.split(':', 1)

        if 'display_text' in node_args:
            display_content_nodelist = node_args['display_text'].get_content_nodelist()
        else:
            display_content_nodelist = None

        node.llm_ref_info = {
            'ref_type_and_target': (ref_type, ref_target),
            'display_content_nodelist': display_content_nodelist,
        }
        

    def prepare_delayed_render(self, node, render_context):
        pass

    def render(self, node, render_context):

        fragment_renderer = render_context.fragment_renderer

        ref_type, ref_target = node.llm_ref_info['ref_type_and_target']
        display_content_nodelist = node.llm_ref_info['display_content_nodelist']

        mgr = render_context.feature_render_manager('refs')

        resource_info = node.latex_walker.resource_info

        try:
            ref_instance = mgr.get_ref(ref_type, ref_target, resource_info=resource_info)
        except Exception as e:
            raise LatexWalkerParseError(
                f"Unable to resolve reference to ???{ref_type}:{ref_target}???: {e}",
                pos=node.pos,
            )

        if display_content_nodelist is None:
            if isinstance(ref_instance.formatted_ref_llm_text, LLMFragment):
                display_content_llm = ref_instance.formatted_ref_llm_text
            else:
                display_content_llm = render_context.doc.environment.make_fragment(
                    ref_instance.formatted_ref_llm_text,
                    standalone_mode=True
                )
            display_content_nodelist = display_content_llm.nodes


        return fragment_renderer.render_link(
            'ref',
            ref_instance.target_href,
            display_content_nodelist,
            render_context=render_context,
            annotations=[f'ref-{ref_type}',], # TODO: add annotation for external links etc. ??
        )

