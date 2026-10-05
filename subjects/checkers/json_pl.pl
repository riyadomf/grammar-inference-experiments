use strict; use warnings; use JSON::PP;
open my $m, "<", $ARGV[0] or die; my $i=0; my $j=JSON::PP->new->allow_nonref;
while (my $ln=<$m>){ chomp $ln; my $rc=1; open my $f,"<",$ln or die "$ln: $!"; local $/; my $d=<$f>; close $f; eval { $j->decode($d); $rc=0; 1 } or $rc=1; print "$i $rc\n"; $i++; }
