## = Description =
MultiPaxos implementation for Distributed Algorithims USI 2018

## = Dependencies =

Python==3.6

## = How to run the tests: =

1) Root paxos implementation is inside this
directory:

   ~/MultiPaxos/paxos
   
2) Run all tests in root folder

cd ~/MultiPaxos/

3)  Test consensus with 3 Acceptors

     Acceptors, 2 Proposer, 2 Learners, 2 Clients

    ./run.sh paxos 10000 && ./check_all.sh 

4) Test consensus with 2 Acceptors

      2 Acceptors, 2 Proposer, 2 Learners, 2 Clients 

     ./run_2acceptor.sh paxos 1000 && ./check_all.sh 
     
5) Test no consensus with 1 Acceptor

      1 Acceptors, 2 Proposer, 2 Learners, 2 Clients 
      
     ./run_1acceptor.sh paxos 1000 && ./check_all.sh 
     
6) Test learner catchup: Initially 1 learner and 1 client. Learner 2 and Client 2 comes online, Client 2 proposes additional 100 values, Make sure Learner 2, learns values in total order.

   3 Acceptors, 2 Proposer, 2 Learner, 2 Clients, 

   
   ./run_catchup.sh paxos 1000 && ./check_all.sh 
   
 7) Loss messages: Make sure learners, learn messages in total order
 
   3 Acceptors, 2 Proposer, 2 Learners, 2 Clients
 
   

     
