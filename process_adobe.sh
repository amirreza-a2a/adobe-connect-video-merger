#!/bin/bash

# مسیر پوشه نهایی برای ذخیره ویدیوها
OUTPUT_DIR="$HOME/Downloads/adobeVideo"
mkdir -p "$OUTPUT_DIR"

# مسیر پوشه دانلودها که فایل‌های زیپ در آن قرار دارند
DOWNLOADS_DIR="$HOME/Downloads/adobeZip"

# پوشه موقت برای اکسترکت کردن هر کلاس
TMP_DIR="$DOWNLOADS_DIR/tmp_extract"

echo "🚀 فرآیند خودکارسازی و ترکیب ویدیوهای ادوبی کانکت آغاز شد..."
echo "📂 ویدیوهای نهایی در این مسیر ذخیره می‌شوند: $OUTPUT_DIR"
echo "--------------------------------------------------------"

# ورود به پوشه دانلودها
cd "$DOWNLOADS_DIR" || exit

counter=1

# ۱. لیست فایل‌های شماره‌دار (مرتب‌شده بر اساس شماره به صورت الفبایی/عددی پیش‌فرض)
numbered_files=$(ls [0-9]*.zip 2>/dev/null)

# ۲. لیست فایل‌های بدون شماره (مرتب‌شده بر اساس زمان دانلود از قدیمی به جدید)
unnumbered_files=$(ls -tr [!0-9]*.zip 2>/dev/null)

# ۳. ترکیب دو لیست (ابتدا شماره‌دارها، سپس بدون شماره‌ها)
all_files="$numbered_files $unnumbered_files"

for zip_file in $all_files; do
    if [ -f "$zip_file" ]; then
        # فرمت دادن به شماره‌گذاری (به صورت 01, 02, 03 و...)
        formatted_counter=$(printf "%02d" $counter)
        
        echo "📦 [$formatted_counter] در حال پردازش فایل زیپ: $zip_file"
        
        # ساخت پوشه موقت و اکسترکت کردن فایل زیپ به صورت بی‌صدا (-q)
        mkdir -p "$TMP_DIR"
        unzip -q "$zip_file" -d "$TMP_DIR"
        
        # ورود به پوشه موقت
        cd "$TMP_DIR" || continue
        
        # اجرای اسکریپت پایتون هوشمند
        if command -v mergeVideoAdobe.py &> /dev/null; then
            mergeVideoAdobe.py
        else
            # دستور کمکی در صورتی که به هر دلیل PATH در لحظه اجرا لود نشده باشد
            python3 "$HOME/Scripts/mergeVideoAdobe.py"
        fi
        
        # بررسی وجود فایل .mp4 و انتقال آن با همان پسوند
        if [ -f "final_class_synced.mp4" ]; then
            mv "final_class_synced.mp4" "$OUTPUT_DIR/class_$formatted_counter.mp4"
            echo "✅ ویدیو با موفقیت به نام class_$formatted_counter.mp4 ذخیره شد."
        else
            echo "❌ خطا: فایل خروجی برای $zip_file ایجاد نشد."
        fi
        
        # بازگشت به پوشه دانلودها و پاکسازی فایل‌های اکسترکت شده برای پارت بعدی
        cd "$DOWNLOADS_DIR" || exit
        rm -rf "$TMP_DIR"
        
        echo "--------------------------------------------------------"
        ((counter++))
    fi
done

echo "✨ تمام فایل‌ها با موفقیت پردازش شدند!"