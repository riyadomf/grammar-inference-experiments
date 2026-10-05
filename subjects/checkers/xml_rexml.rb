# Require one root and no non-whitespace text outside it.
require "rexml/document"
def ok(p)
  doc = REXML::Document.new(p)
  roots = doc.children.count{|c| c.is_a?(REXML::Element)}
  stray = doc.children.any?{|c| c.is_a?(REXML::Text) && c.to_s.strip != ""}
  roots == 1 && !stray
rescue REXML::ParseException
  false
end
File.foreach(ARGV[0]).each_with_index{|ln,i| puts "#{i} #{ok(File.read(ln.chomp)) ? 0 : 1}"}
