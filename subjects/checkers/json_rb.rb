require "json"
File.foreach(ARGV[0]).each_with_index do |ln,i|
  p=ln.chomp
  input = File.read(p)
  ok = begin; JSON.parse(input); true; rescue JSON::ParserError; false; end
  puts "#{i} #{ok ? 0 : 1}"
end
