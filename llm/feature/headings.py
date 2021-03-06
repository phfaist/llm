
#from pylatexenc import macrospec

from ..llmspecinfo import HeadingMacro

from ._base import Feature



class FeatureHeadings(Feature):
    r"""
    Add support for headings via LaTeX commands, including ``\section``,
    ``\subsection``, ``\subsubsection``, ``\paragraph``, etc.
    """

    feature_name = 'headings'
    # no managers needed
    DocumentManager = None
    RenderManager = None

    class SectionCommandSpec:
        def __init__(self, cmdname, inline=False):
            super().__init__()
            self.cmdname = cmdname
            self.inline = inline
        def __repr__(self):
            return (
                f"{self.__class__.__name__}(cmdname={self.cmdname!r}, "
                f"inline={self.inline!r})"
            )

    def __init__(self, section_commands_by_level=None):
        super().__init__()
        if section_commands_by_level is None:
            section_commands_by_level = {
                1: self.SectionCommandSpec(r"section"),
                2: self.SectionCommandSpec(r"subsection"),
                3: self.SectionCommandSpec(r"subsubsection"),
                4: self.SectionCommandSpec(r"paragraph", inline=True),
                5: self.SectionCommandSpec(r"subparagraph", inline=True),
                6: self.SectionCommandSpec(r"subsubparagraph", inline=True),
            }

        def _mkspecobj(x):
            if isinstance(x, self.SectionCommandSpec):
                return x
            if isinstance(x, str):
                return self.SectionCommandSpec(x)
            return self.SectionCommandSpec(**x)

        self.section_commands_by_level = {
            level: _mkspecobj(x)
            for level, x in section_commands_by_level.items()
        }

    def add_latex_context_definitions(self):
        return dict(
            macros=[
                HeadingMacro(
                    macroname=sectioncmdspec.cmdname,
                    heading_level=level,
                    inline_heading=sectioncmdspec.inline,
                )
                for level, sectioncmdspec in self.section_commands_by_level.items()
            ]
        )

