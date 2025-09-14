// customers_analytics.js - تحليل العملاء الشامل

// تحميل البيانات عند فتح الصفحة
document.addEventListener('DOMContentLoaded', function() {
    loadBranches(); // تحميل قائمة الفروع أولاً
    loadCustomersOverview();
    loadTopCustomersByRevenue();
    loadTopCustomersByFrequency();
    loadCustomersByCity();
    loadMonthlyTrends();
    
    // إعداد الفلاتر
    setupFilters();
});

// تحميل قائمة الفروع
async function loadBranches() {
    try {
        const response = await fetch('/api/branches');
        const data = await response.json();
        
        if (data.status === 'success') {
            const branchSelect = document.getElementById('branch-select');
            branchSelect.innerHTML = '<option value="">كل الفروع</option>';
            
            data.data.forEach(branch => {
                const option = document.createElement('option');
                option.value = branch.name;
                option.textContent = `${branch.name} (${branch.order_count} طلب)`;
                branchSelect.appendChild(option);
            });
        }
    } catch (error) {
        console.error('خطأ في تحميل قائمة الفروع:', error);
    }
}

// إعداد الفلاتر
function setupFilters() {
    // تعيين التواريخ الافتراضية
    const today = new Date();
    const firstDayOfMonth = new Date(today.getFullYear(), today.getMonth(), 1);
    
    document.getElementById('start-date').value = firstDayOfMonth.toISOString().split('T')[0];
    document.getElementById('end-date').value = today.toISOString().split('T')[0];
    
    // فلاتر سريعة
    document.getElementById('monthly-btn').addEventListener('click', function() {
        applyQuickFilter('monthly');
    });
    
    document.getElementById('quarterly-btn').addEventListener('click', function() {
        applyQuickFilter('quarterly');
    });
    
    // تطبيق الفلاتر
    document.getElementById('apply-filters-btn').addEventListener('click', function() {
        applyCustomFilters();
    });
    
    // فلتر الشهر
    const monthPicker = document.getElementById('month-picker');
    if (monthPicker) {
        monthPicker.addEventListener('change', function() {
            const selectedMonth = new Date(this.value + '-01');
            const startDate = new Date(selectedMonth.getFullYear(), selectedMonth.getMonth(), 1);
            const endDate = new Date(selectedMonth.getFullYear(), selectedMonth.getMonth() + 1, 0);
            
            document.getElementById('start-date').value = startDate.toISOString().split('T')[0];
            document.getElementById('end-date').value = endDate.toISOString().split('T')[0];
            
            applyCustomFilters();
        });
    }
}

// فلاتر سريعة
function applyQuickFilter(type) {
    const today = new Date();
    let startDate, endDate = today.toISOString().split('T')[0];
    
    if (type === 'monthly') {
        startDate = new Date(today.getFullYear(), today.getMonth(), 1).toISOString().split('T')[0];
    } else if (type === 'quarterly') {
        startDate = new Date(today.getFullYear(), today.getMonth() - 3, 1).toISOString().split('T')[0];
    }
    
    document.getElementById('start-date').value = startDate;
    document.getElementById('end-date').value = endDate;
    
    applyCustomFilters();
}

// تطبيق الفلاتر المخصصة
function applyCustomFilters() {
    const startDate = document.getElementById('start-date').value;
    const endDate = document.getElementById('end-date').value;
    const branch = document.getElementById('branch-select').value;
    
    // عرض رسالة تحميل
    showLoadingMessage();
    
    // تحديث جميع البيانات مع الفلاتر
    Promise.all([
        loadCustomersOverview(startDate, endDate, branch),
        loadTopCustomersByRevenue(startDate, endDate, branch),
        loadTopCustomersByFrequency(startDate, endDate, branch),
        loadCustomersByCity(startDate, endDate, branch),
        loadMonthlyTrends(startDate, endDate, branch)
    ]).then(() => {
        hideLoadingMessage();
    }).catch(error => {
        console.error('خطأ في تطبيق الفلاتر:', error);
        hideLoadingMessage();
    });
}

// عرض رسالة تحميل
function showLoadingMessage() {
    const sections = [
        'customers-overview-content',
        'top-customers-revenue-content', 
        'top-customers-frequency-content',
        'customers-by-city-content',
        'monthly-trends-content'
    ];
    
    sections.forEach(sectionId => {
        const element = document.getElementById(sectionId);
        if (element) {
            element.innerHTML = '<div class="loading-message"><i class="fas fa-spinner fa-spin"></i> جاري تحميل البيانات...</div>';
        }
    });
}

// إخفاء رسالة تحميل
function hideLoadingMessage() {
    // لا نحتاج لعمل شيء هنا لأن البيانات ستحل محل رسالة التحميل
}

// دالة مساعدة لبناء URL parameters
function buildFilterParams(startDate, endDate, branch) {
    const params = new URLSearchParams();
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    if (branch) params.append('branch', branch);
    return params.toString();
}

// تحميل نظرة عامة على العملاء مع KPI Cards
async function loadCustomersOverview(startDate, endDate, branch) {
    try {
        const filterParams = buildFilterParams(startDate, endDate, branch);
        const url = `/api/customers-overview${filterParams ? '?' + filterParams : ''}`;
        const response = await fetch(url);
        const data = await response.json();
        
        if (data.status === 'success') {
            displayCustomersKPIs(data.data);
        } else {
            console.error('خطأ في تحميل نظرة العملاء:', data.message);
        }
    } catch (error) {
        console.error('خطأ في تحميل نظرة العملاء:', error);
    }
}

// عرض KPI Cards للعملاء
function displayCustomersKPIs(data) {
    const container = document.getElementById('customers-overview-content');
    
    const html = `
        <div class="kpi-cards-grid">
            <div class="kpi-card customers-count">
                <div class="kpi-icon">
                    <i class="fas fa-users"></i>
                </div>
                <div class="kpi-content">
                    <h3>إجمالي العملاء</h3>
                    <div class="kpi-value">${parseInt(data.total_customers).toLocaleString()}</div>
                    <div class="kpi-subtitle">عميل نشط</div>
                </div>
            </div>
            
            <div class="kpi-card orders-count">
                <div class="kpi-icon">
                    <i class="fas fa-shopping-cart"></i>
                </div>
                <div class="kpi-content">
                    <h3>إجمالي الطلبات</h3>
                    <div class="kpi-value">${parseInt(data.total_orders).toLocaleString()}</div>
                    <div class="kpi-subtitle">طلب تم تنفيذه</div>
                </div>
            </div>
            
            <div class="kpi-card revenue-total">
                <div class="kpi-icon">
                    <i class="fas fa-dollar-sign"></i>
                </div>
                <div class="kpi-content">
                    <h3>إجمالي الإيرادات</h3>
                    <div class="kpi-value">${data.total_revenue} ر.س</div>
                    <div class="kpi-subtitle">من جميع العملاء</div>
                </div>
            </div>
            
            <div class="kpi-card avg-order">
                <div class="kpi-icon">
                    <i class="fas fa-calculator"></i>
                </div>
                <div class="kpi-content">
                    <h3>متوسط قيمة الطلب</h3>
                    <div class="kpi-value">${data.avg_order_value} ر.س</div>
                    <div class="kpi-subtitle">لكل طلب</div>
                </div>
            </div>
            
            <div class="kpi-card avg-customer">
                <div class="kpi-icon">
                    <i class="fas fa-user-tag"></i>
                </div>
                <div class="kpi-content">
                    <h3>متوسط قيمة العميل</h3>
                    <div class="kpi-value">${data.avg_customer_value} ر.س</div>
                    <div class="kpi-subtitle">إجمالي لكل عميل</div>
                </div>
            </div>
            
            <div class="kpi-card orders-per-customer">
                <div class="kpi-icon">
                    <i class="fas fa-sync-alt"></i>
                </div>
                <div class="kpi-content">
                    <h3>متوسط الطلبات للعميل</h3>
                    <div class="kpi-value">${data.avg_orders_per_customer}</div>
                    <div class="kpi-subtitle">طلب لكل عميل</div>
                </div>
            </div>
        </div>
    `;
    
    container.innerHTML = html;
}

// تحميل أفضل العملاء حسب الإيرادات
async function loadTopCustomersByRevenue(startDate, endDate, branch) {
    try {
        const filterParams = buildFilterParams(startDate, endDate, branch);
        const url = `/api/top-customers-by-revenue?limit=15${filterParams ? '&' + filterParams : ''}`;
        const response = await fetch(url);
        const data = await response.json();
        
        if (data.status === 'success') {
            displayTopCustomersRevenue(data.data);
        } else {
            document.getElementById('top-customers-revenue-content').innerHTML = 
                '<div class="error-message">خطأ في تحميل البيانات</div>';
        }
    } catch (error) {
        console.error('خطأ في تحميل أفضل العملاء:', error);
        document.getElementById('top-customers-revenue-content').innerHTML = 
            '<div class="error-message">خطأ في تحميل البيانات</div>';
    }
}

// عرض أفضل العملاء حسب الإيرادات
function displayTopCustomersRevenue(customers) {
    const container = document.getElementById('top-customers-revenue-content');
    
    let html = `
        <div class="table-responsive">
            <table class="modern-table">
                <thead>
                    <tr>
                        <th>المرتبة</th>
                        <th>اسم العميل</th>
                        <th>رقم الهاتف</th>
                        <th>عنوان التوصيل</th>
                        <th>إجمالي الإيرادات</th>
                        <th>عدد الطلبات</th>
                        <th>متوسط قيمة الطلب</th>
                        <th>أيام النشاط</th>
                        <th>النسبة %</th>
                        <th>أول طلب</th>
                        <th>آخر طلب</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    customers.forEach((customer, index) => {
        html += `
            <tr>
                <td class="rank-cell">
                    <span class="rank-badge rank-${index + 1}">#${index + 1}</span>
                </td>
                <td class="customer-name">${customer.customer_name}</td>
                <td class="phone-number">${customer.phone_number}</td>
                <td class="delivery-address">${customer.delivery_address}</td>
                <td class="currency">${customer.total_revenue} ر.س</td>
                <td class="orders-count">${customer.total_orders}</td>
                <td class="currency">${customer.avg_order_value} ر.س</td>
                <td class="active-days">${customer.active_days}</td>
                <td class="percentage">${customer.revenue_percentage}%</td>
                <td class="date">${customer.first_order}</td>
                <td class="date">${customer.last_order}</td>
            </tr>
        `;
    });
    
    html += '</tbody></table></div>';
    container.innerHTML = html;
}

// تحميل أكثر العملاء تكراراً
async function loadTopCustomersByFrequency(startDate, endDate, branch) {
    try {
        const filterParams = buildFilterParams(startDate, endDate, branch);
        const url = `/api/top-customers-by-frequency?limit=15${filterParams ? '&' + filterParams : ''}`;
        const response = await fetch(url);
        const data = await response.json();
        
        if (data.status === 'success') {
            displayTopCustomersFrequency(data.data);
        } else {
            document.getElementById('top-customers-frequency-content').innerHTML = 
                '<div class="error-message">خطأ في تحميل البيانات</div>';
        }
    } catch (error) {
        console.error('خطأ في تحميل العملاء الأكثر تكراراً:', error);
        document.getElementById('top-customers-frequency-content').innerHTML = 
            '<div class="error-message">خطأ في تحميل البيانات</div>';
    }
}

// عرض أكثر العملاء تكراراً
function displayTopCustomersFrequency(customers) {
    const container = document.getElementById('top-customers-frequency-content');
    
    let html = `
        <div class="table-responsive">
            <table class="modern-table">
                <thead>
                    <tr>
                        <th>المرتبة</th>
                        <th>اسم العميل</th>
                        <th>رقم الهاتف</th>
                        <th>عدد الطلبات</th>
                        <th>إجمالي المبلغ</th>
                        <th>متوسط قيمة الطلب</th>
                        <th>أيام التسوق</th>
                        <th>معدل الطلبات الشهري</th>
                        <th>مدة العضوية (يوم)</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    customers.forEach((customer, index) => {
        html += `
            <tr>
                <td class="rank-cell">
                    <span class="rank-badge rank-${index + 1}">#${index + 1}</span>
                </td>
                <td class="customer-name">${customer.customer_name}</td>
                <td class="phone-number">${customer.phone_number}</td>
                <td class="orders-count">${customer.order_frequency}</td>
                <td class="currency">${customer.total_spent} ر.س</td>
                <td class="currency">${customer.avg_order_value} ر.س</td>
                <td class="shopping-days">${customer.unique_shopping_days}</td>
                <td class="monthly-rate">${customer.monthly_order_rate}</td>
                <td class="lifetime-days">${customer.customer_lifetime_days}</td>
            </tr>
        `;
    });
    
    html += '</tbody></table></div>';
    container.innerHTML = html;
}

// تحميل توزيع العملاء حسب المدن
async function loadCustomersByCity(startDate, endDate, branch) {
    try {
        const filterParams = buildFilterParams(startDate, endDate, branch);
        const url = `/api/customers-by-city${filterParams ? '?' + filterParams : ''}`;
        const response = await fetch(url);
        const data = await response.json();
        
        if (data.status === 'success') {
            displayCustomersByCity(data.data);
        } else {
            document.getElementById('customers-by-city-content').innerHTML = 
                '<div class="info-message">بيانات المدن غير متوفرة</div>';
        }
    } catch (error) {
        console.error('خطأ في تحميل توزيع المدن:', error);
        document.getElementById('customers-by-city-content').innerHTML = 
            '<div class="error-message">خطأ في تحميل البيانات</div>';
    }
}

// عرض توزيع العملاء حسب المدن
function displayCustomersByCity(cities) {
    const container = document.getElementById('customers-by-city-content');
    
    let html = `
        <div class="table-responsive">
            <table class="modern-table">
                <thead>
                    <tr>
                        <th>المدينة</th>
                        <th>عدد العملاء</th>
                        <th>إجمالي الإيرادات</th>
                        <th>عدد الطلبات</th>
                        <th>متوسط قيمة العميل</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    cities.forEach(city => {
        html += `
            <tr>
                <td class="city-name">${city.city}</td>
                <td class="customer-count">${city.customer_count}</td>
                <td class="currency">${city.city_revenue} ر.س</td>
                <td class="orders-count">${city.city_orders}</td>
                <td class="currency">${city.avg_customer_value} ر.س</td>
            </tr>
        `;
    });
    
    html += '</tbody></table></div>';
    container.innerHTML = html;
}

// تحميل الاتجاهات الشهرية
async function loadMonthlyTrends(startDate, endDate, branch) {
    try {
        const filterParams = buildFilterParams(startDate, endDate, branch);
        const url = `/api/monthly-customer-trends${filterParams ? '?' + filterParams : ''}`;
        const response = await fetch(url);
        const data = await response.json();
        
        if (data.status === 'success') {
            displayMonthlyTrends(data.data);
        } else {
            document.getElementById('monthly-trends-content').innerHTML = 
                '<div class="error-message">خطأ في تحميل البيانات</div>';
        }
    } catch (error) {
        console.error('خطأ في تحميل الاتجاهات الشهرية:', error);
        document.getElementById('monthly-trends-content').innerHTML = 
            '<div class="error-message">خطأ في تحميل البيانات</div>';
    }
}

// عرض الاتجاهات الشهرية
function displayMonthlyTrends(trends) {
    const container = document.getElementById('monthly-trends-content');
    
    let html = `
        <div class="table-responsive">
            <table class="modern-table">
                <thead>
                    <tr>
                        <th>الشهر</th>
                        <th>عملاء فريدون</th>
                        <th>إجمالي الطلبات</th>
                        <th>إجمالي الإيرادات</th>
                        <th>متوسط الإيرادات للعميل</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    trends.forEach(trend => {
        html += `
            <tr>
                <td class="month-year">${trend.month_year}</td>
                <td class="customers-count">${trend.unique_customers}</td>
                <td class="orders-count">${trend.total_orders}</td>
                <td class="currency">${trend.total_revenue} ر.س</td>
                <td class="currency">${trend.avg_revenue_per_customer} ر.س</td>
            </tr>
        `;
    });
    
    html += '</tbody></table></div>';
    container.innerHTML = html;
}