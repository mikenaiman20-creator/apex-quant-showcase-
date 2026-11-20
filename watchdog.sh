#!/bin/bash
DB_PATH="/home/ubuntu/apex-quant/state/trials.db"
LOG_FILE="/home/ubuntu/apex-quant/logs/watchdog.log"
CURRENT_COUNT=$(sqlite3 $DB_PATH "SELECT COUNT(*) FROM trials;")
echo $CURRENT_COUNT > /tmp/apex_trial_count.tmp

if [ -f /tmp/apex_trial_count.prev ]; then
    PREV_COUNT=$(cat /tmp/apex_trial_count.prev)
    if [ "$CURRENT_COUNT" -eq "$PREV_COUNT" ]; then
        echo "$(date) - WARNING: Stuck at $CURRENT_COUNT. Restarting..." >> $LOG_FILE
        docker restart apex_researcher
    else
        echo "$(date) - OK: Count moved from $PREV_COUNT to $CURRENT_COUNT." >> $LOG_FILE
    fi
else
    echo "$(date) - Watchdog initialized. Count: $CURRENT_COUNT." >> $LOG_FILE
fi
mv /tmp/apex_trial_count.tmp /tmp/apex_trial_count.prev
