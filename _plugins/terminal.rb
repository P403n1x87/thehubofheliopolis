module Jekyll
  class Terminal < Liquid::Block
    def initialize(tag_name, markup, tokens)
       super
       @prompt = markup
    end

    def render(context)
      n = super.lines.count - 1
      if @prompt.length > 0 then
        p = ([@prompt] * n).join("\n")
        c = "<div class=\"pad-right\"><pre>#{p}</pre></div><div><pre>#{super}</pre></div>"
      else
        c = "<div><pre>#{super}</pre></div>"
      end

      # "<div class=\"terminal\"><div class=\"terminal-header\">Terminal</div><div class=\"terminal-body flex-container flex-row\">#{c}</div></div>"
      "<div class=\"terminal\"><div class=\"terminal-body flex-container flex-row\">#{c}</div></div>"
    end
  end
end

Liquid::Template.register_tag('terminal', Jekyll::Terminal)
