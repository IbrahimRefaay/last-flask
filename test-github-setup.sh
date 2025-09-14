#!/bin/bash
# test-github-setup.sh - اختبار إعداد GitHub Actions

echo "🧪 اختبار إعداد نظام تحديث المخزون"
echo "=================================="

# تحقق من وجود الملفات المطلوبة
echo "📁 فحص الملفات المطلوبة..."

if [ -f ".github/workflows/stock-update.yml" ]; then
    echo "✅ GitHub Actions workflow موجود"
else
    echo "❌ ملف GitHub Actions غير موجود"
    exit 1
fi

if [ -d "data-push" ]; then
    echo "✅ مجلد data-push موجود"
    
    if [ -f "data-push/inventory.py" ]; then
        echo "✅ inventory.py موجود"
    else
        echo "⚠️ inventory.py غير موجود"
    fi
    
    if [ -f "data-push/historical_inv.py" ]; then
        echo "✅ historical_inv.py موجود"
    else
        echo "⚠️ historical_inv.py غير موجود"
    fi
    
else
    echo "❌ مجلد data-push غير موجود"
    exit 1
fi

if [ -f "requirements.txt" ]; then
    echo "✅ requirements.txt موجود"
else
    echo "⚠️ requirements.txt غير موجود"
fi

echo ""
echo "📋 قائمة المتطلبات للإعداد:"
echo "1. إضافة GCP_SERVICE_ACCOUNT_KEY في GitHub Secrets"
echo "2. إضافة STOCK_UPDATE_TOKEN في GitHub Secrets"  
echo "3. إضافة APP_WEBHOOK_URL في GitHub Secrets"
echo "4. تعيين STOCK_UPDATE_TOKEN في متغيرات البيئة للخادم"

echo ""
echo "🚀 للاختبار:"
echo "1. انتقل إلى GitHub → Actions → Stock Data Update → Run workflow"
echo "2. أو اضغط زر التحديث في واجهة التطبيق"

echo ""
echo "✨ الإعداد مكتمل! راجع ملف STOCK_UPDATE_SETUP.md للتفاصيل"
