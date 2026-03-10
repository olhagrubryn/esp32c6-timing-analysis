# fix_format_strings.sh
#!/bin/bash

+
cd ~/BA/esp32c6-timing-analysis-1-backup/components/generated_tests


for file in *.c; do
    echo "Fixing $file..."
    
   
    sed -i '/#include <stdio.h>/a #include <inttypes.h>' "$file"
    
    
    sed -i 's/printf(".*%u/printf("%" PRIu32/g' "$file"
    sed -i 's/%u cycles/%" PRIu32 " cycles/g' "$file"
    sed -i 's/%u,/"%" PRIu32 ",/g' "$file"
done


if [ -f "collector.c" ]; then
    sed -i 's/printf("  Run %d: %u cycles/printf("  Run %d: %" PRIu32 " cycles/g' collector.c
    sed -i 's/printf("  Average: %u cycles total/printf("  Average: %" PRIu32 " cycles total/g' collector.c
    sed -i 's/printf("CSV,%s,%u,/printf("CSV,%s,%" PRIu32 ",/g' collector.c
fi

echo "Format strings fixed!"