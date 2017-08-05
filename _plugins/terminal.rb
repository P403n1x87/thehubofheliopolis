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
        c = '
<pre style="float:left;padding-right: 0px;">' << p     << '</pre>
<pre style="padding-left: 0px;">' << super << '</pre>
'
      else
        c = '<pre>' << super << '</pre>'
      end

      '<figure class="terminal">' << c << '</figure>'
    end
  end
end

Liquid::Template.register_tag('terminal', Jekyll::Terminal)
