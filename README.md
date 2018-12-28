## = Description =
MultiPaxos implementation for Distributed Algorithims USI 2018

## = Dependencies =

Python==3.6

## = How to run the tests: =

1) Root paxos implementation is inside this
directory:

   ~/MultiPaxos/paxos

Your *.sh scripts should be directly inside it
(e.g. ~/MultiPaxos/paxos/acceptor.sh) and should work when called
from inside the directory itself.

2) Run one of the "run*.sh" from inside THIS folder. When the run
finishes, run "check_all.sh" to check the output of the run. For
example:

    cd ~/MultiPaxos/
    ./run.sh paxos 10000 && ./check_all.sh 

3) After a run ends, run "check_all.sh" to see if everything went OK.
"Test 3" might FAIL in some cases, but with few proposed values and no message
loss it should also be OK.

