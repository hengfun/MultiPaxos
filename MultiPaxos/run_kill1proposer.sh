#!/usr/bin/env bash

projdir="$1"
conf=`pwd`/paxos.conf
n="$2"
cmd="python3.6 ./paxos.py /home/heng/Documents/MultiPaxos/MultiPaxos/paxos.conf proposer 1"

if [[ x$projdir == "x" || x$n == "x" ]]; then
	echo "Usage: $0 <project dir> <number of values per proposer>"
    exit 1
fi

# following line kills processes that have the config file in its cmdline
KILLCMD="pkill -f $conf"
KILLCMD2="pkill -f -9 $cmd"
$KILLCMD

cd $projdir

../generate.sh $n > ../prop1
../generate.sh $n > ../prop2

echo "starting acceptors..."

./acceptor.sh 1 $conf &
./acceptor.sh 2 $conf &
./acceptor.sh 3 $conf &

sleep 1
echo "starting learners..."

./learner.sh 1 $conf > ../learn1 &
./learner.sh 2 $conf > ../learn2 &

sleep 1
echo "starting proposers..."

./proposer.sh 1 $conf &
./proposer.sh 2 $conf &

echo "waiting to start clients"
sleep 2
echo "starting clients..."

./client.sh 1 $conf < ../prop1 &
echo "killing 1 proposer"
sleep 3
pkill -f -9 "/paxos.conf proposer 1"
echo "waiting to elect second proposer"
sleep 8
echo "client 2 starts proposing"
./client.sh 2 $conf < ../prop2 &

sleep 5

$KILLCMD
wait

cd ..
