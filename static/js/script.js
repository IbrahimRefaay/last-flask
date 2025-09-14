// Global variables for query parameters
let currentQueryParams = '';

// --- Helper function to show a loading spinner ---
function showLoader(elementId) {
    document.getElementById(elementId).innerHTML = '<div class="loader"></div>';
}

// --- Function to update dynamic title based on filters ---
function updateDynamicTitle(queryString = '') {
    const titleElement = document.getElementById('dynamic-title');
    const subtitleElement = document.getElementById('date-subtitle');
    
    if (!queryString || queryString === '?') {
        titleElement.innerHTML = '<i class="fas fa-chart-line"></i> تحليل المبيعات';
        subtitleElement.textContent = 'اختر فترة لعرض البيانات';
        return;
    }
    
    const params = new URLSearchParams(queryString.replace('?', ''));
    const filterType = params.get('filter');
    const singleDay = params.get('single_day');
    const startDay = params.get('start_day');
    const endDay = params.get('end_day');
    const startDate = params.get('start_date');
    const endDate = params.get('end_date');
    const branch = params.get('branch');
    const month = params.get('month');
    
    let title = '<i class="fas fa-chart-line"></i> تحليل المبيعات';
    let subtitle = '';
    
    // تحديد النص حسب نوع الفلتر
    if (filterType === 'date_range' && startDate && endDate) {
        const startFormatted = new Date(startDate).toLocaleDateString('ar');
        const endFormatted = new Date(endDate).toLocaleDateString('ar');
        title += ` من ${startFormatted} إلى ${endFormatted}`;
        subtitle = `بيانات الفترة من ${startFormatted} إلى ${endFormatted}`;
    } else if (filterType === 'monthly') {
        title += month ? ` عن شهر ${month}` : ' عن الشهر الحالي';
        subtitle = month ? `بيانات شهر ${month}` : 'بيانات الشهر الحالي';
    } else if (filterType === 'mid_monthly') {
        title += ' عن النصف الأول من الشهر';
        subtitle = 'بيانات النصف الأول من الشهر';
    } else if (filterType === 'day_in_month' && month && singleDay) {
        title += ` عن يوم ${singleDay} في شهر ${month}`;
        subtitle = `بيانات يوم ${singleDay} في شهر ${month}`;
    } else if (filterType === 'days_range_in_month' && month && startDay && endDay) {
        title += ` من يوم ${startDay} إلى يوم ${endDay} في شهر ${month}`;
        subtitle = `من يوم ${startDay} إلى يوم ${endDay} في شهر ${month}`;
    } else if (singleDay) {
        try {
            const dayName = getDayName(singleDay);
            const currentDate = new Date();
            const currentYear = currentDate.getFullYear();
            const currentMonth = (currentDate.getMonth() + 1).toString().padStart(2, '0');
            const dayFormatted = singleDay.toString().padStart(2, '0');
            const fullDate = `${dayFormatted}-${currentMonth}-${currentYear}`;
            title += ` عن يوم ${dayName}`;
            subtitle = `بيانات يوم ${fullDate}`;
        } catch (error) {
            const currentDate = new Date();
            const currentYear = currentDate.getFullYear();
            const currentMonth = (currentDate.getMonth() + 1).toString().padStart(2, '0');
            const dayFormatted = singleDay.toString().padStart(2, '0');
            const fullDate = `${dayFormatted}-${currentMonth}-${currentYear}`;
            title += ` عن يوم ${singleDay}`;
            subtitle = `بيانات يوم ${fullDate}`;
        }
    } else if (startDay && endDay) {
        try {
            const startDayName = getDayName(startDay);
            const endDayName = getDayName(endDay);
            const currentDate = new Date();
            const currentYear = currentDate.getFullYear();
            const currentMonth = (currentDate.getMonth() + 1).toString().padStart(2, '0');
            const startDayFormatted = startDay.toString().padStart(2, '0');
            const endDayFormatted = endDay.toString().padStart(2, '0');
            const startFullDate = `${startDayFormatted}-${currentMonth}-${currentYear}`;
            const endFullDate = `${endDayFormatted}-${currentMonth}-${currentYear}`;
            title += ` من ${startDayName} إلى ${endDayName}`;
            subtitle = `من ${startFullDate} إلى ${endFullDate}`;
        } catch (error) {
            const currentDate = new Date();
            const currentYear = currentDate.getFullYear();
            const currentMonth = (currentDate.getMonth() + 1).toString().padStart(2, '0');
            const startDayFormatted = startDay.toString().padStart(2, '0');
            const endDayFormatted = endDay.toString().padStart(2, '0');
            const startFullDate = `${startDayFormatted}-${currentMonth}-${currentYear}`;
            const endFullDate = `${endDayFormatted}-${currentMonth}-${currentYear}`;
            title += ` من يوم ${startDay} إلى يوم ${endDay}`;
            subtitle = `من ${startFullDate} إلى ${endFullDate}`;
        }
    }
    
    // إضافة اسم الفرع إذا تم تحديده
    if (branch && branch !== '') {
        title += ` - فرع ${branch}`;
        subtitle += ` - فرع ${branch}`;
    }
    
    titleElement.innerHTML = title;
    subtitleElement.textContent = subtitle;
}

// --- Helper function to get day name in Arabic ---
function getDayName(dateInput) {
    // إذا كان رقم اليوم فقط، أضف الشهر والسنة الحالية
    let date;
    if (typeof dateInput === 'string' && !dateInput.includes('-') && !dateInput.includes('/')) {
        const currentDate = new Date();
        const currentYear = currentDate.getFullYear();
        const currentMonth = currentDate.getMonth() + 1; // getMonth() returns 0-11
        date = new Date(`${currentYear}-${currentMonth.toString().padStart(2, '0')}-${dateInput.padStart(2, '0')}`);
    } else {
        date = new Date(dateInput);
    }
    
    const days = ['الأحد', 'الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت'];
    return days[date.getDay()];
}

// --- Helper function to get API parameters ---
function getApiParams() {
    const daySelector = document.getElementById('day-selector')?.value || '';
    const startDay = document.getElementById('start-day')?.value || '';
    const endDay = document.getElementById('end-day')?.value || '';
    const startDate = document.getElementById('start-date')?.value || '';
    const endDate = document.getElementById('end-date')?.value || '';
    const branch = document.getElementById('branch-select')?.value || '';
    const monthPicker = document.getElementById('month-picker')?.value || '';

    let params = new URLSearchParams();

    // Clear conflicting filters first
    const hasDateRange = startDate && endDate;
    const hasMonthFilter = monthPicker;
    const hasDayFilters = daySelector || (startDay && endDay);

    // Priority 1: Full date range (most specific)
    if (hasDateRange) {
        params.append('start_date', startDate);
        params.append('end_date', endDate);
        params.append('filter', 'date_range');
    }
    // Priority 2: Month-based filters
    else if (hasMonthFilter) {
        params.append('month', monthPicker);
        
        if (daySelector) {
            params.append('single_day', daySelector);
            params.append('filter', 'day_in_month');
        } else if (startDay && endDay) {
            params.append('start_day', startDay);
            params.append('end_day', endDay);
            params.append('filter', 'days_range_in_month');
        } else {
            params.append('filter', 'monthly');
        }
    }
    // Priority 3: Current month day filters
    else if (daySelector) {
        params.append('single_day', daySelector);
        params.append('filter', 'single_day');
    } else if (startDay && endDay) {
        params.append('start_day', startDay);
        params.append('end_day', endDay);
        params.append('filter', 'days_range');
    }

    // Always add branch if selected
    if (branch) {
        params.append('branch', branch);
    }

    return '?' + params.toString();
}

// --- Function to clear all filters ---
function clearAllFilters() {
    document.getElementById('day-selector').value = '';
    document.getElementById('start-day').value = '';
    document.getElementById('end-day').value = '';
    document.getElementById('start-date').value = '';
    document.getElementById('end-date').value = '';
    document.getElementById('month-picker').value = '';
    // Don't clear branch filter as it's independent
}

// --- Function to clear specific filter types ---
function clearConflictingFilters(keepType) {
    if (keepType !== 'date') {
        document.getElementById('start-date').value = '';
        document.getElementById('end-date').value = '';
    }
    
    if (keepType !== 'month') {
        document.getElementById('month-picker').value = '';
    }
    
    if (keepType !== 'day') {
        document.getElementById('day-selector').value = '';
        document.getElementById('start-day').value = '';
        document.getElementById('end-day').value = '';
    }
}

// --- Main function to update all dashboard data ---
function updateAllDashboardData(queryString = '') {
    currentQueryParams = queryString;
    
    // تحديث العنوان الديناميكي
    updateDynamicTitle(queryString);
    
    const allButtons = document.querySelectorAll('.filters button');
    allButtons.forEach(btn => btn.classList.remove('active'));
    if (queryString.includes('filter=')) {
        const filterType = new URLSearchParams(queryString).get('filter');
        document.getElementById(`${filterType}-btn`)?.classList.add('active');
    } else if (queryString) {
        document.getElementById('manual-fetch-btn').classList.add('active');
    }

    // Call all individual fetch functions
    fetchKPIs(queryString);
    fetchServicesDetails(queryString);
    fetchSalesDetails(queryString);
    fetchBranchSales(queryString);
    fetchBranchProfits(queryString);
    fetchTopCategories(queryString);
    fetchTopCategoriesByProfit(queryString);
    fetchTopSellers(queryString);
    fetchTop10Sellers(queryString);
    fetchTopProductsBySalesValue(queryString);
    fetchTopProductsByQuantity(queryString);
    fetchTopProductsByProfit(queryString);
    fetchTopCategoriesByReturns(queryString);
    fetchTopSellersByReturns(queryString);
    
    // Load new advanced analytics
    fetchTop10Categories(queryString);
    fetchTop15Customers(queryString);
    fetchStockProducts(queryString);
}

// --- Generic Table Fetching Function ---
function fetchAndRenderTable(endpoint, containerId, title, columns, rowGenerator) {
    const tableContent = document.getElementById(containerId);
    showLoader(containerId);
    
    // Add query parameters to endpoint if it doesn't already have them
    const finalEndpoint = endpoint + (endpoint.includes('?') ? '&' : '?') + getApiParams().substring(1);
    
    fetch(finalEndpoint).then(res => res.json()).then(data => {
        if (data.status === 'success' && data.data.length > 0) {
            let html = `<h2>${title}</h2><table class="details-table"><thead><tr>`;
            columns.forEach(col => html += `<th>${col}</th>`);
            html += `</tr></thead><tbody>`;
            data.data.forEach(row => {
                html += rowGenerator(row);
            });
            tableContent.innerHTML = html + `</tbody></table>`;
        } else {
            tableContent.innerHTML = '';
        }
    }).catch(err => {
        console.error(`Error fetching ${containerId}:`, err);
        tableContent.innerHTML = `<div class="message-box error">فشل تحميل البيانات.</div>`;
    });
}

// --- Individual Data Fetching Functions ---
function fetchKPIs(queryString) {
    const kpiContent = document.getElementById('kpi-content');
    showLoader('kpi-content');

    // Define the exact order of keys you want the cards to appear in
    const kpiOrder = [
        "إجمالي المبيعات",
        "المبيعات بدون خدمات",
        "الربح",
        "هامش الربح",
        "عدد الفواتير",
        "عدد العملاء",
        "إجمالي القطع المباعة",
        "متوسط الفاتورة",
        "المرتجعات (فروع)",
        "قيمة المرتجعات (فروع)",
        "قيمة الخدمات",
        "مرتجعات الخدمات"
    ];

    fetch('/api/data' + queryString).then(res => res.json()).then(data => {
        if (data.status === 'success' && Object.keys(data.data).length > 0) {
            let html = `<h2><i class="fas fa-chart-line"></i> المؤشرات الرئيسية</h2><div class="kpi-grid">`;
            const icons = {
                // Sales Group
                "إجمالي المبيعات": "fas fa-sack-dollar",
                "المبيعات بدون خدمات": "fas fa-shopping-basket",
                
                // Profit Group
                "الربح": "fas fa-chart-pie",
                "هامش الربح": "fas fa-percent",
                
                // Invoices & Customers Group
                "عدد الفواتير": "fas fa-receipt",
                "متوسط الفاتورة": "fas fa-calculator",
                "عدد العملاء": "fas fa-users",
                
                // Quantity Group
                "إجمالي القطع المباعة": "fas fa-cubes",
                
                // Returns Group
                "المرتجعات (فروع)": "fas fa-arrow-rotate-left",
                "قيمة المرتجعات (فروع)": "fas fa-coins",
                
                // Services Group
                "قيمة الخدمات": "fas fa-hands-helping",
                "مرتجعات الخدمات": "fas fa-exchange-alt",
            };

            // Loop through the predefined order to ensure correct display
            for (const key of kpiOrder) {
                const value = data.data[key];
                if (value !== undefined) {
                    const iconClass = icons[key] || "fas fa-chart-bar";
                    const isReturns = key.includes('مرتجعات') || key.includes('المرتجعات');
                    const valueClass = isReturns ? 'kpi-value returns-value' : 'kpi-value';
                    
                    // جعل كارت الخدمات قابل للنقر
                    if (key === "قيمة الخدمات" || key === "مرتجعات الخدمات") {
                        html += `<div class="kpi-card clickable-kpi" onclick="goToServicesPage()" title="انقر لعرض تفاصيل الخدمات"><div class="kpi-title"><i class="${iconClass}"></i> ${key}</div><div class="${valueClass}">${value}</div></div>`;
                    } else {
                        html += `<div class="kpi-card"><div class="kpi-title"><i class="${iconClass}"></i> ${key}</div><div class="${valueClass}">${value}</div></div>`;
                    }
                }
            }
            kpiContent.innerHTML = html + '</div>';
        } else {
            kpiContent.innerHTML = '<div class="message-box">لا توجد بيانات لهذه الفترة.</div>';
        }
    }).catch(err => kpiContent.innerHTML = `<div class="message-box error">فشل تحميل المؤشرات.</div>`);
}
function fetchServicesDetails(queryString) {
    fetchAndRenderTable(`/api/services-details${queryString}`, 'services-table-content', '<i class="fas fa-hands-helping"></i> تفاصيل الخدمات', ['الخدمة', 'إجمالي القيمة'], 
        (row) => `<tr ${row.product.includes('<strong>') ? 'class="total-row"' : ''}><td>${row.product}</td><td>${row.total_value}</td></tr>`
    );
}

function fetchSalesDetails(queryString) {
    fetchAndRenderTable(`/api/sales-details${queryString}`, 'sales-table-content', '<i class="fas fa-shopping-cart"></i> تفاصيل المبيعات حسب جهة الشراء', ['جهة الشراء', 'إجمالي المبيعات', 'النسبة من الإجمالي', 'عدد القطع المباعة', 'هامش الربح'],
        (row) => `<tr ${row.purchase_source.includes('<strong>') ? 'class="total-row"' : ''}><td>${row.purchase_source}</td><td>${row.total_sales}</td><td>${row.rate_by_source}</td><td>${row.total_items_sold}</td><td>${row.profit_margin}</td></tr>`
    );
}

function fetchBranchSales(queryString) {
    fetchAndRenderTable(`/api/branch-sales${queryString}`, 'branch-sales-table-content', '<i class="fas fa-building"></i> مبيعات الفروع', ['الفرع', 'قيمة المبيعات', 'النسبة من الإجمالي', 'عدد القطع المباعة', 'عدد الفواتير', 'عدد العملاء', 'متوسط قيمة الفاتورة'],
        (row) => `<tr ${row.branch.includes('<strong>') ? 'class="total-row"' : ''}><td>${row.branch}</td><td>${row.total_sales}</td><td>${row.sales_percentage}</td><td>${row.total_items_sold}</td><td>${row.invoice_count}</td><td>${row.customer_count}</td><td>${row.avg_invoice_value}</td></tr>`
    );
}

function fetchBranchProfits(queryString) {
    fetchAndRenderTable(`/api/branch-profits${queryString}`, 'branch-profits-table-content', '<i class="fas fa-chart-pie"></i> أرباح الفروع', ['الفرع', 'الربح', 'النسبة من الربح الكلي', 'هامش الربح'],
        (row) => `<tr ${row.branch.includes('<strong>') ? 'class="total-row"' : ''}><td>${row.branch}</td><td>${row.profit}</td><td>${row.profit_percentage}</td><td>${row.profit_margin}</td></tr>`
    );
}

function fetchTopCategories(queryString) {
    const tableContent = document.getElementById('top-categories-table-content');
    showLoader('top-categories-table-content');
    fetch('/api/top-categories' + queryString).then(res => res.json()).then(data => {
        if (data.status === 'success' && data.data.length > 0) {
            let html = `<h2><i class="fas fa-sitemap"></i> أكثر 5 فئات مبيعاً</h2><table class="details-table">
                            <thead><tr><th>اسم الفئة</th><th>جهة الشراء</th><th>قيمة المبيعات</th><th>الكمية المباعة</th><th>النسبة داخل الفئة</th><th>الأرباح</th></tr></thead><tbody>`;
            data.data.forEach(category => {
                const rowspan = category.sources.length + 1;
                category.sources.forEach((source, index) => {
                    html += `<tr>`;
                    if (index === 0) html += `<td rowspan="${rowspan}">${category.category_name}</td>`;
                    html += `<td>${source.purchase_source}</td><td>${source.total_sales}</td><td>${source.total_items_sold}</td><td>${source.rate_within_category}</td><td>${source.profit}</td></tr>`;
                });
                html += `<tr class="total-row"><td>الإجمالي</td><td>${(category.category_total_sales).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td><td>${(category.category_total_items).toLocaleString('en-US')}</td><td>100.00%</td><td>${(category.category_total_profit).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td></tr>`;
            });
            tableContent.innerHTML = html + `</tbody></table>`;
        } else {
            tableContent.innerHTML = '';
        }
    }).catch(err => tableContent.innerHTML = `<div class="message-box error">فشل تحميل أكثر الفئات مبيعاً.</div>`);
}

function fetchTopCategoriesByProfit(queryString) {
    const tableContent = document.getElementById('top-categories-by-profit-table-content');
    showLoader('top-categories-by-profit-table-content');
    fetch('/api/top-categories-by-profit' + queryString).then(res => res.json()).then(data => {
        if (data.status === 'success' && data.data.length > 0) {
            let html = `<h2><i class="fas fa-trophy"></i> أكثر 5 فئات ربحاً</h2><table class="details-table">
                            <thead><tr><th>اسم الفئة</th><th>جهة الشراء</th><th>الأرباح</th><th>هامش الربح</th><th>الكمية المباعة</th><th>المبيعات</th></tr></thead><tbody>`;
            data.data.forEach(category => {
                const rowspan = category.sources.length + 1;
                category.sources.forEach((source, index) => {
                    html += `<tr>`;
                    if (index === 0) html += `<td rowspan="${rowspan}">${category.category_name}</td>`;
                    html += `<td>${source.purchase_source}</td><td>${source.profit}</td><td>${source.profit_margin}</td><td>${source.total_items_sold}</td><td>${source.total_sales}</td></tr>`;
                });
                const total_profit_margin = (category.category_total_profit / (category.category_total_sales / 1.15)) * 100 || 0;
                html += `<tr class="total-row"><td>الإجمالي</td><td>${(category.category_total_profit).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td><td>${total_profit_margin.toFixed(2)}%</td><td>${(category.category_total_items).toLocaleString('en-US')}</td><td>${(category.category_total_sales).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td></tr>`;
            });
            tableContent.innerHTML = html + `</tbody></table>`;
        } else {
            tableContent.innerHTML = '';
        }
    }).catch(err => tableContent.innerHTML = `<div class="message-box error">فشل تحميل أكثر الفئات ربحاً.</div>`);
}

function fetchTopSellers(queryString) {
    fetchAndRenderTable(`/api/top-sellers${queryString}`, 'top-sellers-table-content', '<i class="fas fa-users"></i> أفضل بائع لكل فرع', ['اسم البائع', 'الفرع', 'قيمة المبيعات', 'نسبة مبيعاته من الفرع', 'عدد القطع', 'عدد الفواتير', 'متوسط الفاتورة', 'الأرباح', 'هامش الربح', 'أيام العمل'],
        (row) => `<tr><td>${row.employee_name}</td><td>${row.branch}</td><td>${row.total_sales}</td><td>${row.sales_percentage_in_branch}</td><td>${row.total_items_sold}</td><td>${row.invoice_count}</td><td>${row.avg_invoice_value}</td><td>${row.profit}</td><td>${row.profit_margin}</td><td>${row.work_days || 'N/A'}</td></tr>`
    );
}

function fetchTop10Sellers(queryString) {
    fetchAndRenderTable(`/api/top-10-sellers${queryString}`, 'top-10-sellers-table-content', '<i class="fas fa-trophy"></i> أكثر 10 بائعين', ['اسم البائع', 'الفرع', 'قيمة المبيعات', 'نسبة مبيعاته من الفرع', 'عدد القطع', 'عدد الفواتير', 'متوسط الفاتورة', 'الأرباح', 'هامش الربح', 'أيام العمل'],
        (row) => `<tr><td>${row.employee_name}</td><td>${row.branch}</td><td>${row.total_sales}</td><td>${row.sales_percentage_in_branch}</td><td>${row.total_items_sold}</td><td>${row.invoice_count}</td><td>${row.avg_invoice_value}</td><td>${row.profit}</td><td>${row.profit_margin}</td><td>${row.work_days || 'N/A'}</td></tr>`
    );
}

function fetchStockProducts(queryString) {
    fetchAndRenderTable(`/api/stock-products${queryString}`, 'stock-products-content', '<i class="fas fa-boxes"></i> أفضل 20 منتج مع المخزون', ['الباركود', 'اسم المنتج', 'عدد القطع المباعة', 'قيمة المبيعات', 'الأرباح', 'المخزون الحالي', 'حالة المخزون'],
        (row) => `<tr class="${row.stock_status_class || ''}"><td>${row.product_barcode || ''}</td><td>${row.product_name}</td><td>${row.total_quantity}</td><td>${row.total_sales}</td><td>${row.total_profit}</td><td>${row.current_stock}</td><td>${row.stock_status}</td></tr>`
    );
}

function fetchTopProductsBySalesValue(queryString) {
    fetchAndRenderTable(`/api/top_products_by_sales_value${queryString}`, 'top-products-by-sales-value-content', '<i class="fas fa-sack-dollar"></i> أكثر المنتجات مبيعاً (بالقيمة)', ['الباركود', 'اسم المنتج', 'عدد القطع', 'قيمة المبيعات'],
        (row) => `<tr><td>${row.product_barcode || ''}</td><td>${row.product_name}</td><td>${row.total_quantity}</td><td>${row.total_sales}</td></tr>`
    );
}

function fetchTopProductsByQuantity(queryString) {
    fetchAndRenderTable(`/api/top_products_by_quantity${queryString}`, 'top-products-by-quantity-content', '<i class="fas fa-cubes"></i> أكثر المنتجات مبيعاً (بالكمية)', ['الباركود', 'اسم المنتج', 'عدد القطع', 'قيمة المبيعات'],
        (row) => `<tr><td>${row.product_barcode || ''}</td><td>${row.product_name}</td><td>${row.total_quantity}</td><td>${row.total_sales}</td></tr>`
    );
}

function fetchTopProductsByProfit(queryString) {
    fetchAndRenderTable(`/api/top_products_by_profit${queryString}`, 'top-products-by-profit-content', '<i class="fas fa-coins"></i> أكثر المنتجات ربحية', ['الباركود', 'اسم المنتج', 'عدد القطع', 'الأرباح'],
        (row) => `<tr><td>${row.product_barcode || ''}</td><td>${row.product_name}</td><td>${row.total_quantity}</td><td>${row.total_profit}</td></tr>`
    );
}

function fetchTopCategoriesByReturns(queryString) {
    fetchAndRenderTable(`/api/top_categories_by_returns${queryString}`, 'top-categories-by-returns-content', '<i class="fas fa-arrow-rotate-left"></i> أكثر الفئات من حيث المرتجعات', ['الفئة', 'عدد القطع المرتجعة', 'قيمة المرتجعات'],
        (row) => `<tr ${row.category_name.includes('<strong>') ? 'class="total-row"' : ''}><td>${row.category_name}</td><td>${row.returned_quantity}</td><td>${row.returned_value}</td></tr>`
    );
}

function viewCustomerInvoices(phoneNumber) {
    console.log('📞 viewCustomerInvoices called with phone number:', phoneNumber);
    console.log('📞 Phone number type:', typeof phoneNumber);
    console.log('📞 Phone number length:', phoneNumber ? phoneNumber.length : 'N/A');
    
    if (!phoneNumber || phoneNumber.trim() === '') {
        console.error('❌ Phone number is empty or invalid:', phoneNumber);
        alert('رقم الهاتف غير محدد');
        return;
    }
    
    // Get current filter parameters
    const currentParams = getApiParams();
    const customerUrl = `/customer/${encodeURIComponent(phoneNumber)}?phone=${encodeURIComponent(phoneNumber)}${currentParams.substring(1) ? '&' + currentParams.substring(1) : ''}`;
    
    console.log('🔗 Final customer URL:', customerUrl);
    console.log('📋 Current params:', currentParams);
    
    window.location.href = customerUrl;  // Changed from window.open to same window
}

function fetchTopSellersByReturns(queryString) {
    fetchAndRenderTable(`/api/top_sellers_by_returns${queryString}`, 'top-sellers-by-returns-content', '<i class="fas fa-user-slash"></i> أكثر البائعين من حيث المرتجعات', ['الفرع', 'اسم الموظف', 'عدد القطع المرتجعة', 'قيمة المرتجعات'],
        (row) => `<tr ${row.branch.includes('<strong>') ? 'class="total-row"' : ''}><td>${row.branch}</td><td>${row.employee_name}</td><td>${row.returned_quantity}</td><td>${row.returned_value}</td></tr>`
    );
}

function fetchTop10Categories(queryString) {
    fetchAndRenderTable(`/api/top-10-categories${queryString}`, 'top-10-categories-table-content', '<i class="fas fa-layer-group"></i> أهم 10 فئات بالكمية والمبلغ', ['اسم الفئة', 'إجمالي المبيعات', 'الكمية الإجمالية', 'عدد المصادر', 'الأرباح', 'هامش الربح'],
        (row) => `<tr ${row.category_name.includes('<strong>') ? 'class="total-row"' : ''}><td>${row.category_name}</td><td>${row.total_subtotal}</td><td>${row.total_quantity}</td><td>${row.source_count}</td><td>${row.total_profit}</td><td>${row.profit_margin}</td></tr>`
    );
}

function fetchTop15Customers(queryString) {
    fetchAndRenderTable(`/api/top-15-customers${queryString}`, 'top-15-customers-table-content', '<i class="fas fa-user-friends"></i> أهم 15 عميل مع التفاصيل الكاملة', ['اسم العميل', 'رقم الهاتف', 'الفرع', 'إجمالي المبيعات', 'الكمية', 'عدد الفواتير', 'الأرباح', 'أيام الزيارة', 'متوسط قيمة الفاتورة', 'هامش الربح'],
        (row) => {
            if (row.customer_name.includes('<strong>')) {
                return `<tr class="total-row"><td>${row.customer_name}</td><td>${row.phone_number}</td><td>${row.branch}</td><td>${row.total_subtotal}</td><td>${row.total_quantity}</td><td>${row.receipt_count}</td><td>${row.total_profit}</td><td>${row.visit_days}</td><td>${row.avg_receipt_value}</td><td>${row.profit_margin}</td></tr>`;
            } else {
                return `<tr><td><a href="#" onclick="viewCustomerInvoices('${row.phone_number}')" class="customer-link" title="عرض فواتير العميل">${row.customer_name}</a></td><td>${row.phone_number}</td><td>${row.branch}</td><td>${row.total_subtotal}</td><td>${row.total_quantity}</td><td>${row.receipt_count}</td><td>${row.total_profit}</td><td>${row.visit_days}</td><td>${row.avg_receipt_value}</td><td>${row.profit_margin}</td></tr>`;
            }
        }
    );
}

// --- Load branches and populate day selectors ---
function loadBranches() {
    fetch('/api/get-branches').then(res => res.json()).then(data => {
        if (data.status === 'success') {
            const branchSelect = document.getElementById('branch-select');
            data.data.forEach(branch => {
                const option = document.createElement('option');
                option.value = branch;
                option.textContent = branch;
                branchSelect.appendChild(option);
            });
        }
    }).catch(err => console.error('Error loading branches:', err));
}

function populateDaySelectors(maxDay = 31) {
    const daySelector = document.getElementById('day-selector');
    const startDaySelector = document.getElementById('start-day');
    const endDaySelector = document.getElementById('end-day');

    // Save current values
    const currentDay = daySelector.value;
    const currentStart = startDaySelector.value;
    const currentEnd = endDaySelector.value;

    // Remove all except the first option
    [daySelector, startDaySelector, endDaySelector].forEach(sel => {
        while (sel.options.length > 1) sel.remove(1);
    });

    for (let i = 1; i <= maxDay; i++) {
        const option1 = document.createElement('option');
        option1.value = i;
        option1.textContent = i;
        daySelector.appendChild(option1);

        const option2 = document.createElement('option');
        option2.value = i;
        option2.textContent = i;
        startDaySelector.appendChild(option2);

        const option3 = document.createElement('option');
        option3.value = i;
        option3.textContent = i;
        endDaySelector.appendChild(option3);
    }

    // Restore values if still valid, else clear
    if (currentDay && currentDay <= maxDay) daySelector.value = currentDay; else daySelector.value = '';
    if (currentStart && currentStart <= maxDay) startDaySelector.value = currentStart; else startDaySelector.value = '';
    if (currentEnd && currentEnd <= maxDay) endDaySelector.value = currentEnd; else endDaySelector.value = '';
}

// --- Helper function to get days in a month ---
function getDaysInMonth(year, month) {
    return new Date(year, month, 0).getDate();
}

// --- Function to populate days for a specific month ---
function populateDaysForMonth(year, month) {
    const daysInMonth = getDaysInMonth(year, month);
    populateDaySelectors(daysInMonth);
}

// --- Function to populate days for current month ---
function populateDaysForCurrentMonth() {
    const today = new Date();
    const daysInCurrentMonth = getDaysInMonth(today.getFullYear(), today.getMonth() + 1);
    populateDaySelectors(daysInCurrentMonth);
}

// --- Smooth scrolling function for navigation ---
function scrollToSection(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.scrollIntoView({
            behavior: 'smooth',
            block: 'start'
        });
        
        // Add highlight effect
        element.style.transition = 'background-color 0.5s ease';
        element.style.backgroundColor = 'rgba(72, 209, 204, 0.1)';
        setTimeout(() => {
            element.style.backgroundColor = '';
        }, 2000);
    }
}

// --- Event Listeners ---
document.addEventListener('DOMContentLoaded', function() {
    // Load branches and populate day selectors
    loadBranches();
    populateDaySelectors(31);
    
    // Load initial data (monthly filter by default)
    updateAllDashboardData('?filter=monthly');


    // Month filter event
    const monthPicker = document.getElementById('month-picker');
    if (monthPicker) {
        monthPicker.addEventListener('change', function() {
            // Clear other date filters
            document.getElementById('day-selector').value = '';
            document.getElementById('start-day').value = '';
            document.getElementById('end-day').value = '';
            const selectedMonth = this.value; // format: yyyy-mm
            if (selectedMonth) {
                // Get max days in month
                const [year, month] = selectedMonth.split('-').map(Number);
                const maxDay = new Date(year, month, 0).getDate();
                populateDaySelectors(maxDay);
                updateAllDashboardData(`?filter=monthly&month=${selectedMonth}`);
            } else {
                populateDaySelectors(31);
            }
        });
    }

    // Quick filter buttons
    document.getElementById('mid-monthly-btn').addEventListener('click', () => {
        // Clear day selectors and month picker when using quick filters
        document.getElementById('day-selector').value = '';
        document.getElementById('start-day').value = '';
        document.getElementById('end-day').value = '';
        if (monthPicker) monthPicker.value = '';
        updateAllDashboardData('?filter=mid_monthly');
    });

    document.getElementById('monthly-btn').addEventListener('click', () => {
        // Clear day selectors and month picker when using quick filters
        document.getElementById('day-selector').value = '';
        document.getElementById('start-day').value = '';
        document.getElementById('end-day').value = '';
        if (monthPicker) monthPicker.value = '';
        updateAllDashboardData('?filter=monthly');
    });

    // Manual date range button
    document.getElementById('manual-fetch-btn').addEventListener('click', () => {
        updateAllDashboardData(getApiParams());
    });

    // Day selector change - clear range selectors
    document.getElementById('day-selector').addEventListener('change', () => {
        if (document.getElementById('day-selector').value) {
            document.getElementById('start-day').value = '';
            document.getElementById('end-day').value = '';
        }
        // Auto-update if month is selected
        const monthValue = document.getElementById('month-picker').value;
        if (monthValue && document.getElementById('day-selector').value) {
            updateAllDashboardData(getApiParams());
        }
    });

    // Range selectors change - clear single day selector
    document.getElementById('start-day').addEventListener('change', () => {
        if (document.getElementById('start-day').value) {
            document.getElementById('day-selector').value = '';
        }
        // Auto-update if both range days and month are selected
        const monthValue = document.getElementById('month-picker').value;
        const endDayValue = document.getElementById('end-day').value;
        if (monthValue && document.getElementById('start-day').value && endDayValue) {
            updateAllDashboardData(getApiParams());
        }
    });

    document.getElementById('end-day').addEventListener('change', () => {
        if (document.getElementById('end-day').value) {
            document.getElementById('day-selector').value = '';
        }
        // Auto-update if both range days and month are selected
        const monthValue = document.getElementById('month-picker').value;
        const startDayValue = document.getElementById('start-day').value;
        if (monthValue && startDayValue && document.getElementById('end-day').value) {
            updateAllDashboardData(getApiParams());
        }
    });

    // Branch filter change
    document.getElementById('branch-select').addEventListener('change', () => {
        if (currentQueryParams) {
            updateAllDashboardData(currentQueryParams + '&' + getApiParams().substring(1));
        } else {
            updateAllDashboardData(getApiParams());
        }
    });

    // Date range inputs - clear conflicting filters when used
    document.getElementById('start-date').addEventListener('change', () => {
        if (document.getElementById('start-date').value) {
            clearConflictingFilters('date');
        }
    });

    document.getElementById('end-date').addEventListener('change', () => {
        if (document.getElementById('end-date').value) {
            clearConflictingFilters('date');
        }
    });

    // Month picker - clear conflicting filters
    document.getElementById('month-picker').addEventListener('change', function() {
        if (this.value) {
            clearConflictingFilters('month');
            // Populate days for selected month
            const [year, month] = this.value.split('-').map(Number);
            populateDaysForMonth(year, month);
        } else {
            populateDaysForCurrentMonth();
        }
    });

    // Day selector change - clear range selectors and conflicting filters
    document.getElementById('day-selector').addEventListener('change', () => {
        if (document.getElementById('day-selector').value) {
            document.getElementById('start-day').value = '';
            document.getElementById('end-day').value = '';
            clearConflictingFilters('day');
        }
    });

    // Range selectors change - clear single day selector and conflicting filters
    document.getElementById('start-day').addEventListener('change', () => {
        if (document.getElementById('start-day').value) {
            document.getElementById('day-selector').value = '';
            clearConflictingFilters('day');
        }
    });

    document.getElementById('end-day').addEventListener('change', () => {
        if (document.getElementById('end-day').value) {
            document.getElementById('day-selector').value = '';
            clearConflictingFilters('day');
        }
    });

    // Branch filter change (independent, doesn't clear other filters)
    document.getElementById('branch-select').addEventListener('change', () => {
        // Just trigger update without clearing other filters
        const params = getApiParams();
        if (params !== '?') {
            updateAllDashboardData(params);
        }
    });

    // Add clear all filters button functionality
    const clearFiltersBtn = document.createElement('button');
    clearFiltersBtn.textContent = 'مسح جميع الفلاتر';
    clearFiltersBtn.className = 'btn-secondary';
    clearFiltersBtn.style.marginLeft = '10px';
    clearFiltersBtn.addEventListener('click', () => {
        clearAllFilters();
        updateAllDashboardData('');
    });
    
    // Add the clear button to the first filter group
    const firstFilterGroup = document.querySelector('.filter-group');
    if (firstFilterGroup) {
        firstFilterGroup.appendChild(clearFiltersBtn);
    }
});

// دالة الانتقال لصفحة الخدمات مع الاحتفاظ بالفلاتر
function goToServicesPage() {
    // الحصول على الفلاتر الحالية
    const fromDate = document.getElementById('fromDate')?.value || '';
    const toDate = document.getElementById('toDate')?.value || '';
    const branchFilter = document.getElementById('branchFilter')?.value || '';
    
    // إنشاء URL parameters بالأسماء الصحيحة للخدمات
    const params = new URLSearchParams();
    if (fromDate) params.append('start_date', fromDate);
    if (toDate) params.append('end_date', toDate);
    if (branchFilter) params.append('branch', branchFilter);
    
    const servicesUrl = `/services${params.toString() ? '?' + params.toString() : ''}`;
    window.location.href = servicesUrl;
}