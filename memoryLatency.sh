#!/bin/bash
#    Changelog:
#       10/18/2024 - Added sysbench THREADS 
#       10/17/2024 - Added Engineering's suggested parameters changes.
#       10/14/2024 - Added run loop run terminator from hardcoded value
#                     variable.
#                    Created for loop for Hana SQL runs.
#                    Increased Hana SQL runs from 3 to 5 per Venkat's 
#                     suggestion.
#                    Fixed error when trying to stat non existent 
#                     memoryLatency.log on first run
#                    Fixed error when systems do not have SUSEConnect
#                     installed (i.e., leap, TW, etc).
#       10/13/2024 - Moved Hana SQL & sysbench code to own functions
#       10/10/2024 - Create function to check auto-install sysbench pkg if not
#                     installed.
#       10/09/2024 - Added /proc/vmstat, /proc/meminfo and cpu util output
#                     to log collection for future data correlation.
#       10/08/2024 - Added logrotate once log size reaches user defined 
#                     number of megabytes.
#       10/07/2024 - Initial version


######### Changes these values ONLY!!!!#########
MS=160         # Size of memoryLatency.log file
               # before compressing in Megabytes

BLKSIZE="1024M"  # sysbench memory-block-size=$BLKSIZE
                 # See the README file on this setting.

MEMSIZE="10G"   # sysbench memory-total-size=$MEMSIZE
NUMTHREADS="1"  # sysbench threads=$NUMTHREADS
################################################

usr="$1"
dbusr="$2"
paswd="$3"
BS=1048576
opSize=17739               # Size of output text per run
FS=$((${MS}*${BS}))
NOW=$(date ${DATETZ}  +%s.%6N)
D=$(date -u -d "@${NOW}" +'%Y-%m-%dT%T.%6N')
#workdir=$(pwd)
workdir=/tmp
hanaHost="$(hostname -s)"
NUMRUNS=5
L="/var/log/memtest/memoryLatency.log"

mkdir $(dirname ${L}) > /dev/null 2>&1

checksysbenchPkg() {
    # Linux memory test requires sysbench pkg
    p=$(rpm -qi sysbench)
    if [[ "${p}" =~ "not installed" ]]; then
        echo "sysbench package not installed."
        if ! [ -f /usr/sbin/SUSEConnect ]; then
            echo "Please install sysbench pkg using following command:"
            echo "   zypper -n --no-refresh in sysbench."
            exit -1
        fi
        repo="$(SUSEConnect --list-extensions | egrep 'SUSE Package Hub' | awk '{print $7}')"
        if [ "${repo}" == "(Activated)" ]; then
            echo "Found PackageHub repo."
        else
            echo "Found PackageHub repo not enabled.  Enabling PackageHub repo."
            cmd=$(sudo SUSEConnect --list-extensions | egrep -A1 'SUSE Package Hub' | tail -1)
            cmd=${cmd#*:}
            $cmd > /dev/null
        fi
        echo "Installing sysbench."
        zypper -n --no-refresh in sysbench > /dev/null
    fi
}

checkLogrotate() {
    # archive if log file over $FS size

    if ! [ -f ${L} ]; then
        return
    fi
    fileSize=$(stat -c%s ${L})
    if (( ${fileSize} >= ${FS} )); then
        /usr/bin/xz --no-sparse -z ${L}
        /usr/bin/mv ${L}.xz ${L}-${D}.xz 
    fi
}

runHanaMemTest() {
    echo "*** Running Hana HANA_Tests_MemoryOperations.txt ***" >> ${L} 2>&1

    echo "sudo su - ${usr} -c \"hdbsql -n ${hanaHost} -i 00 -u ${dbusr} -p '${paswd}' -I ${workdir}/HANA_Tests_MemoryOperations.txt\"" >> ${L} 2>&1
    s1=$(date +%s.%3N)			# %3N is milliseconds
    for(( i=0; i < ${NUMRUNS}; i++)) {
       sudo su - ${usr} -c "hdbsql -n ${hanaHost} -i 00 -u ${dbusr} -p '${paswd}' -I ${workdir}/HANA_Tests_MemoryOperations.txt" >> ${L} 2>&1
    }
    e1=$(date +%s.%3N)

    echo "Elapsed time: e1: ${e1} - ${s1} $(echo "scale=6;(${e1}-${s1})*1000" | bc -l ) ms" >> ${L} 2>&1
    echo "" >> ${L} 2>&1
}

runHanaMemTestResult() {
   echo "sudo su - ${usr} -c \"hdbsql -n ${hanaHost} -i 00 -u ${dbusr} -p '${paswd}' -I ${workdir}/HANA_Tests_Results.txt\"" >> ${L} 2>&1
   s1=$(date +%s.%3N)
   sudo su - ${usr} -c "hdbsql -n ${hanaHost} -i 00 -u ${dbusr} -p '${paswd}' -I ${workdir}/HANA_Tests_Results.txt" >> ${L} 2>&1
   e1=$(date +%s.%3N)
   echo "Elapsed time: e1: ${e1} - ${s1} $(echo "scale=6;(${e1}-${s1})*1000" | bc -l ) ms" >> ${L} 2>&1

   echo "" >> ${L} 2>&1
}

runSysBench() {
   echo "***Running sysbench memory test 1***" >> ${L} 2>&1
   s1=$(date +%s.%3N)
   for(( i=0; i < ${NUMRUNS}; i++)) {
       echo "sysbench --memory-block-size=${BLKSIZE} --threads=${NUMTHREADS} --memory-total-size=${MEMSIZE} --memory-hugetlb=off --memory-oper=write --memory-access-mode=seq memory run" >> ${L} 2>&1
       sysbench --memory-block-size=${BLKSIZE} --threads=${NUMTHREADS} --memory-total-size=${MEMSIZE} --memory-hugetlb=off --memory-oper=write --memory-access-mode=seq memory run >> ${L} 2>&1
       echo "sysbench --memory-block-size=${BLKSIZE} --threads=${NUMTHREADS}--memory-total-size=${MEMSIZE} --memory-hugetlb=off --memory-oper=read --memory-access-mode=rnd memory run" >> ${L} 2>&1
       sysbench --memory-block-size=${BLKSIZE} --threads=${NUMTHREADS} --memory-total-size=${MEMSIZE} --memory-hugetlb=off --memory-oper=read --memory-access-mode=rnd memory run >> ${L} 2>&1
   }
   e1=$(date +%s.%3N)
   echo "***Running sysbench memory test 2***" >> ${L} 2>&1
   echo "Elapsed time: e1: ${e1} - ${s1} $(echo "scale=6;(${e1}-${s1})*1000" | bc -l ) ms" >> ${L} 2>&1

   echo "" >> ${L} 2>&1
}

checksysbenchPkg
checkLogrotate

echo "#====" >> "$L"
echo "${D} " >> "$L"
echo "${NOW} " >> "$L"
echo "#====" >> "$L"

runHanaMemTest
runHanaMemTestResult
runSysBench

# Capture vmstat data
echo "*** cat /proc/vmstat 1***" >> ${L} 2>&1
cat /proc/vmstat >> ${L} 2>&1
echo "*** cat /proc/vmstat 2***" >> ${L} 2>&1
echo "" >> ${L} 2>&1

# Capture meminfo data
echo "*** cat /proc/meminfo 1***" >> ${L} 2>&1
cat /proc/meminfo >> ${L} 2>&1 
echo "*** cat /proc/meminfo 2***" >> ${L} 2>&1
echo "" >> ${L} 2>&1

# Capture top output
echo "*** top -b -n 1|head -5 1***" >> ${L} 2>&1
top -b -n 1|head -5 >> ${L} 2>&1 
echo "*** top -b -n 1|head -5 2***" >> ${L} 2>&1
echo "" >> ${L} 2>&1
