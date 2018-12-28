= Dependencies =

Python==3.6

= How to run the tests: =

1) Place the root of your paxos implementation inside this
directory. For example, if you have the folder:

   ~/MultiPaxos/paxos

Your *.sh scripts should be directly inside it
(e.g. ~/MultiPaxos/paxos/acceptor.sh) and should work when called
from inside the directory itself.

2) Run one of the "run*.sh" from inside THIS folder. When the run
finishes, run "check_all.sh" to check the output of the run. For
example:

    cd ~/MultiPaxos/
    ./run.sh paxos 100  # each client will submit 100 values
    # wait for the run to finish
    ./check_all.sh # check the run

3) After a run ends, run "check_all.sh" to see if everything went OK.
"Test 3" might FAIL in some cases, but with few proposed values and no message
loss it should also be OK.

= Caveats/Tips =

a) If you are using a "hardcoded" named network interface
(e.g. "eth0"), you must make it hardcoded inside your bash scripts
instead (which is then as a parameter to your actual implementation
for example). I can change the interface name inside the bash scripts.

b) The scripts will try to "kill" your processes (SIGTERM).
You might need to "flush" the output of your learners to
make sure values are printed when learned.

c) The output of your "learners" should be ONLY the values learned,
one per line. Anything else will fail the checks.

d) The scripts wait some seconds after starting the different
processes, to be sure there is some time for your implementation to
"stabilize". If it is not enough, you should explain why and how to
make it work. There is no reason for it not to work as is though.

e) The scripts wait for around 5 seconds after starting the clients
for values to be learned. Depending on the amount of values proposed
and your implementation, it might not be enough. For around 100-1000
values per client it should be enough time.

f) The "run_loss.sh" script uses a 10% loss probability which you can
change inside the script. It does it by adding a rule/filter with
iptables.  It will also remove it using "loss_unset.sh". If kill the
script for some reason, you might have to call "loss_unset.sh" by
hand to remove the filter.

