
from ._base import FragmentRenderer


class TextFragmentRenderer(FragmentRenderer):

    display_href_urls = True

    #supports_delayed_render_markers = False # -- inherited already

    def render_value(self, value):
        return value

    def render_delayed_marker(self, node, delayed_key, render_context):
        return ''

    def render_delayed_dummy_placeholder(self, node, delayed_key, render_context):
        return '#DELAYED#'

    def render_nothing(self, annotations=None):
        return ''

    def render_empty_error_placeholder(self, debug_str):
        return ''

    def render_text_format(self, text_formats, nodelist, render_context):
        content = self.render_nodelist(
            nodelist,
            render_context,
            is_block_level=False,
        )
        return content
    
    def render_enumeration(self, iter_items_nodelists, counter_formatter, render_context,
                           *, target_id_generator=None, annotations=None, nested_depth=0):

        all_items = []
        for j, item_content_nodelist in enumerate(iter_items_nodelists):

            item_content = self.render_nodelist(
                item_content_nodelist,
                render_context=render_context,
                is_block_level=True,
            )

            tag_nodelist = counter_formatter(1+j)
            if tag_nodelist is None:
                tag_content = '?'
            elif isinstance(tag_nodelist, str):
                tag_content = self.render_value(tag_nodelist)
            else:
                tag_content = self.render_nodelist(
                    tag_nodelist,
                    render_context=render_context,
                    is_block_level=False,
                )
                
            if nested_depth > 0:
                tag_content = " "*(4*nested_depth) + tag_content

            all_items.append(
                (tag_content, item_content),
            )

        if not all_items:
            return self.render_semantic_block('', 'enumeration', annotations=annotations)

        max_item_width = max([ len(fmtcnt) for fmtcnt, item_content in all_items ])

        return self.render_join_blocks([
            self.render_semantic_block(
                self.render_join([
                    self.render_value(fmtcnt.rjust(max_item_width+2, ' ') + ' '),
                    item_content,
                ]),
                'enumeration',
                annotations=annotations,
            )
            for fmtcnt, item_content in all_items
        ])

    def render_heading(self, heading_nodelist, render_context, *,
                       heading_level=1, target_id=None, inline_heading=False,
                       annotations=None):

        rendered_heading = self.render_inline_content(heading_nodelist, render_context)

        def add_punct(x, c):
            x = str(x)
            if x.rstrip()[-1:] in '.,:;?!':
                return x
            return x + c

        if heading_level == 1:
            return f"{rendered_heading}\n{'='*len(rendered_heading)}"
        if heading_level == 2:
            return f"{rendered_heading}\n{'-'*len(rendered_heading)}"
        if heading_level == 3:
            return f"{rendered_heading}\n{'~'*len(rendered_heading)}"
        if heading_level == 4:
            return f"{add_punct(rendered_heading,':')}  "
        if heading_level == 5:
            return f"    {add_punct(rendered_heading,':')}  "
        if heading_level == 6:
            return f"        {add_punct(rendered_heading,':')}  "

        raise ValueError(f"Bad {heading_level=}, expected 1..6")


    def render_verbatim(self, value, *, annotations=None, target_id=None):
        return value

    def render_link(self, ref_type, href, display_nodelist, render_context,
                    annotations=None):
        r"""
        .....

        `href` can be:

        - a URL (external link)
        
        - an anchor fragment only (`#fragment-name`), for links within the
          document; note that we use #fragment-name universally, even if the
          output format is not HTML.  It's up to the output format's render
          context features / fragment renderer subclass implementations to
          translate the linking scheme correctly.
        """

        display_content = self.render_nodelist(
            display_nodelist,
            render_context=render_context,
            is_block_level=False,
        )

        # never display local links (e.g. #footnote-X)
        if self.display_href_urls and not href.startswith("#"):
            return f"{display_content} <{href}>"
        return display_content


    def render_float(self, float_instance, render_context):

        full_figcaption_rendered_list = []
        if float_instance.number is not None:
            full_figcaption_rendered_list.append(
                self.render_join([
                    float_instance.float_type_info.float_caption_name,
                    '??',
                    self.render_nodelist(float_instance.formatted_counter_value_llm.nodes,
                                         render_context=render_context),
                ])
            )
        elif float_instance.caption_nodelist:
            full_figcaption_rendered_list.append(
                float_instance.float_type_info.float_caption_name
            )
        else:
            pass
        
        if float_instance.caption_nodelist:
            full_figcaption_rendered_list.append(
                ": " # filler between the "Figure X" and the rest of the caption text.
            )
            full_figcaption_rendered_list.append(
                self.render_nodelist(
                    float_instance.caption_nodelist,
                    render_context=render_context
                )
            )

        rendered_float_caption = None
        if full_figcaption_rendered_list:
            rendered_float_caption = self.render_join(full_figcaption_rendered_list)

        float_content_block = self.render_nodelist(
            float_instance.content_nodelist,
            render_context=render_context,
            is_block_level=True,
        )

        if rendered_float_caption is not None:
            float_content_with_caption = self.render_join_blocks([
                float_content_block,
                rendered_float_caption,
            ])
        else:
            float_content_with_caption = float_content_block

        fig_sep = '??'*80

        return (
            fig_sep + '\n' + float_content_with_caption + '\n' + fig_sep
        )


    def render_graphics_block(self, graphics_resource):

        return f"{'['+graphics_resource.src_url+']':^80}"
