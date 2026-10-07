import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Brand } from '../components/Brand'
import { Button } from '../components/ui'
import { Icon } from '../components/Icon'

/**
 * White Moon user guide (دليل الاستخدام) — ported from the standalone
 * whitemoon-user-guide.html and reskinned to the "Nightfall" design system.
 * All source content is preserved; the chrome (top bar, table of contents,
 * hero, footer) is rebuilt with the app's tokens and components.
 */

const TOC: { group: string; items: { label: string; id: string; icon: string }[] }[] = [
  {
    group: 'المقدمة',
    items: [
      { label: 'نظرة عامة', id: 'intro-section', icon: 'menu_book' },
      { label: 'الأدوار السبعة', id: 'roles', icon: 'groups' },
      { label: 'الصلاحيات الـ33', id: 'permissions', icon: 'key' },
      { label: 'جدول الصلاحيات', id: 'permissions-table', icon: 'table_chart' },
    ],
  },
  {
    group: 'الفصول',
    items: [
      { label: '1. البدء', id: 'ch1', icon: 'play_circle' },
      { label: '2. إدارة المستخدمين', id: 'ch2', icon: 'manage_accounts' },
      { label: '3. سجل التدقيق', id: 'ch3', icon: 'history' },
      { label: '4. المحاسبة', id: 'ch4', icon: 'account_balance' },
      { label: '5. المخازن', id: 'ch5', icon: 'inventory_2' },
      { label: '6. الائتمان', id: 'ch6', icon: 'credit_score' },
      { label: '7. العمليات', id: 'ch7', icon: 'settings' },
      { label: '8. الإنتاج والشركاء', id: 'ch8', icon: 'precision_manufacturing' },
      { label: '9. الصيانة', id: 'ch9', icon: 'build' },
      { label: '10. الأسئلة الشائعة', id: 'ch10', icon: 'help' },
    ],
  },
  {
    group: 'الملاحق',
    items: [
      { label: 'أ. جدول الصلاحيات', id: 'appendix-a', icon: 'table_chart' },
      { label: 'ب. جدول المسارات', id: 'appendix-b', icon: 'alt_route' },
      { label: 'ج. جهات الاتصال', id: 'appendix-c', icon: 'contact_support' },
      { label: 'د. قاموس المصطلحات', id: 'appendix-d', icon: 'translate' },
    ],
  },
]

const GUIDE_STYLES = `.guide-prose{color:#1a2140;line-height:1.95;font-size:15px}
.guide-prose h2{font-size:26px;font-weight:600;color:#1a2140;margin:44px 0 16px;padding-bottom:10px;border-bottom:2px solid #e7ecf5;scroll-margin-top:84px;position:relative}
.guide-prose h2::before{content:"";position:absolute;bottom:-2px;inset-inline-start:0;width:64px;height:2px;background:#a8812b}
.guide-prose h3{font-size:18px;font-weight:600;color:#2b3a67;margin:30px 0 12px;scroll-margin-top:84px}
.guide-prose p{margin:12px 0}
.guide-prose ul,.guide-prose ol{margin:12px 0;padding-inline-start:26px}
.guide-prose li{margin:7px 0}
.guide-prose strong{font-weight:600;color:#1a2140}
.guide-prose a{color:#2b3a67;text-decoration:underline;text-underline-offset:3px}
.guide-prose a:hover{color:#a8812b}
.guide-prose code{font-family:'JetBrains Mono',ui-monospace,monospace;font-size:.85em;background:rgba(43,58,103,.08);color:#2b3a67;padding:2px 7px;border-radius:6px;direction:ltr;display:inline-block;line-height:1.5}
.guide-prose .table-wrap{overflow-x:auto;margin:18px 0;border:1px solid #e7ecf5;border-radius:16px;box-shadow:0 1px 2px rgba(16,24,53,.06);background:#fff}
.guide-prose table{width:100%;border-collapse:collapse;font-size:14px}
.guide-prose th{background:#eef1f8;color:#2b3a67;font-weight:600;text-align:right;padding:12px 14px;white-space:nowrap;border-bottom:1px solid #e7ecf5}
.guide-prose td{padding:11px 14px;border-top:1px solid #eef1f8;vertical-align:top}
.guide-prose tbody tr:hover{background:#f6f8fc}
.guide-prose .callout{display:flex;gap:12px;padding:16px 18px;border-radius:16px;margin:20px 0;border:1px solid transparent}
.guide-prose .callout-icon{font-size:22px;flex-shrink:0;line-height:1.4}
.guide-prose .callout-title{font-weight:600;margin-bottom:4px}
.guide-prose .callout-content p{margin:4px 0}
.guide-prose .callout.info{background:rgba(43,58,103,.08);border-color:rgba(43,58,103,.16);color:#2b3a67}
.guide-prose .callout.info .callout-content p{color:#3a4672}
.guide-prose .callout.warning{background:rgba(156,103,8,.12);border-color:rgba(156,103,8,.26);color:#9c6708}
.guide-prose .callout.warning .callout-content p{color:#7a5207}
.guide-prose .callout.danger{background:rgba(190,58,43,.10);border-color:rgba(190,58,43,.24);color:#be3a2b}
.guide-prose .callout.danger .callout-content p{color:#8f2a20}
.guide-prose .steps{margin:18px 0;display:flex;flex-direction:column;gap:10px;counter-reset:gstep}
.guide-prose .step{position:relative;background:#fff;border:1px solid #e7ecf5;border-radius:14px;padding:14px 16px;padding-inline-start:54px;box-shadow:0 1px 2px rgba(16,24,53,.05)}
.guide-prose .step::before{counter-increment:gstep;content:counter(gstep);position:absolute;inset-inline-start:14px;top:14px;width:28px;height:28px;border-radius:9px;background:linear-gradient(145deg,#2b3a67,#141b35);color:#fff;display:grid;place-items:center;font-weight:600;font-size:13px;font-family:'JetBrains Mono',monospace}
.guide-prose .step-title{font-weight:600;color:#1a2140}
.guide-prose .step-desc{color:#5b6480;font-size:14px;margin-top:3px}
@media print{.guide-no-print{display:none!important}.guide-prose h2{break-after:avoid}}
`

const GUIDE_HTML = `    <h2 id="intro-section" class="section">نظرة عامة على المنظومة</h2>

    <p><strong>وايت مون</strong> هي منظومة متكاملة بتجمع:</p>

    <ul>
      <li><strong>منصة تجارة إلكترونية B2B</strong> — تجار بيبيعوا لتجار</li>
      <li><strong>نظام ERP كامل</strong> — محاسبة، مخازن، مشتريات، مبيعات، إنتاج</li>
      <li><strong>نظام ائتمان وتحصيل</strong> — إدارة الذمم والتصنيف الائتماني</li>
      <li><strong>نظام لوجستيات</strong> — شحن وتتبع وتوصيل</li>
      <li><strong>نظام تواصل</strong> — شات مقيّد + إشعارات</li>
    </ul>

    <h3>يعني إيه ده عملياً؟</h3>

    <p>لو إنت شركة توزيع، وايت مون بتخليك:</p>

    <ul>
      <li>تدير <strong>موردين</strong> كتير من مكان واحد</li>
      <li>تدير <strong>عملاء</strong> (تجار) بأسعار جملة</li>
      <li>تتابع <strong>المخزون</strong> في كل موقع</li>
      <li>تسجّل <strong>كل قيد محاسبي</strong> تلقائياً</li>
      <li>تصنّف <strong>كل عميل</strong> ائتمانياً</li>
      <li>تصعّد <strong>المتأخرات</strong> تلقائياً</li>
      <li>تشحن <strong>وتتبّع</strong> الشحنات</li>
      <li>تدير <strong>نقاط بيع (POS)</strong> في الفروع</li>
    </ul>

    <!-- ==================== الأدوار ==================== -->
    <h2 id="roles" class="section">الأدوار السبعة</h2>

    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>#</th>
            <th>الدور</th>
            <th>الكود</th>
            <th>مين هو؟</th>
            <th>المسؤولية</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>1</td>
            <td><strong>إدارة عليا</strong></td>
            <td><code>admin.high</code></td>
            <td>مالك الشركة</td>
            <td>كل حاجة</td>
          </tr>
          <tr>
            <td>2</td>
            <td><strong>مدير</strong></td>
            <td><code>admin</code></td>
            <td>مدير تشغيلي</td>
            <td>كل حاجة ما عدا القيود الحساسة</td>
          </tr>
          <tr>
            <td>3</td>
            <td><strong>موظف شركة</strong></td>
            <td><code>staff</code></td>
            <td>موظفين</td>
            <td>مهام يومية</td>
          </tr>
          <tr>
            <td>4</td>
            <td><strong>عميل</strong></td>
            <td><code>customer</code></td>
            <td>تجار</td>
            <td>شراء ومتابعة</td>
          </tr>
          <tr>
            <td>5</td>
            <td><strong>مورد</strong></td>
            <td><code>supplier</code></td>
            <td>موردين</td>
            <td>عروض منتجات</td>
          </tr>
          <tr>
            <td>6</td>
            <td><strong>وكيل</strong></td>
            <td><code>agent</code></td>
            <td>وكيل بمنطقة</td>
            <td>بيع وتحصيل</td>
          </tr>
          <tr>
            <td>7</td>
            <td><strong>فرع</strong></td>
            <td><code>branch</code></td>
            <td>فرع الشركة</td>
            <td>بيع وتحصيل</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- ==================== الصلاحيات ==================== -->
    <h2 id="permissions" class="section">الصلاحيات الـ33</h2>

    <h3>1. صلاحيات الإدارة العليا</h3>
    <div class="table-wrap">
      <table>
        <thead><tr><th>الكود</th><th>المعنى</th></tr></thead>
        <tbody>
          <tr><td><code>*</code></td><td>كل الصلاحيات</td></tr>
          <tr><td><code>admin.high</code></td><td>تفعيل الإدارة العليا</td></tr>
        </tbody>
      </table>
    </div>

    <h3>2. صلاحيات المستخدمين</h3>
    <div class="table-wrap">
      <table>
        <thead><tr><th>الكود</th><th>المعنى</th></tr></thead>
        <tbody>
          <tr><td><code>user.read</code></td><td>عرض المستخدمين</td></tr>
          <tr><td><code>user.impersonate</code></td><td>الدخول كـ مستخدم تاني</td></tr>
          <tr><td><code>supplier.approve</code></td><td>الموافقة على مورد</td></tr>
        </tbody>
      </table>
    </div>

    <h3>3. صلاحيات الائتمان</h3>
    <div class="table-wrap">
      <table>
        <thead><tr><th>الكود</th><th>المعنى</th></tr></thead>
        <tbody>
          <tr><td><code>credit.override</code></td><td>تجاوز السقف</td></tr>
          <tr><td><code>credit.manage</code></td><td>إدارة السقوف</td></tr>
        </tbody>
      </table>
    </div>

    <h3>4. صلاحيات التحصيل</h3>
    <div class="table-wrap">
      <table>
        <thead><tr><th>الكود</th><th>المعنى</th></tr></thead>
        <tbody>
          <tr><td><code>payment.collect</code></td><td>تسجيل سداد</td></tr>
          <tr><td><code>payment.approve</code></td><td>اعتماد السداد</td></tr>
        </tbody>
      </table>
    </div>

    <h3>5. صلاحيات المحاسبة (حساسة)</h3>
    <div class="table-wrap">
      <table>
        <thead><tr><th>الكود</th><th>المعنى</th></tr></thead>
        <tbody>
          <tr><td><code>period.close</code></td><td>إغلاق فترة</td></tr>
          <tr><td><code>period.reopen</code></td><td>فتح فترة مقفولة</td></tr>
          <tr><td><code>high.manual_journal</code></td><td>قيد يدوي</td></tr>
          <tr><td><code>high.manual_journal.closed_period</code></td><td>قيد على فترة مقفولة</td></tr>
          <tr><td><code>high.map.edit</code></td><td>تعديل خريطة القيود</td></tr>
        </tbody>
      </table>
    </div>

    <h3>6. صلاحيات المخازن</h3>
    <div class="table-wrap">
      <table>
        <thead><tr><th>الكود</th><th>المعنى</th></tr></thead>
        <tbody>
          <tr><td><code>product.manage</code></td><td>إدارة الكتالوج</td></tr>
          <tr><td><code>inventory.manage</code></td><td>تعديل الأرصدة</td></tr>
          <tr><td><code>offer.manage</code></td><td>عروض المورد</td></tr>
          <tr><td><code>shortage.resolve</code></td><td>حسم النواقص</td></tr>
        </tbody>
      </table>
    </div>

    <h3>7. صلاحيات الطلبات</h3>
    <div class="table-wrap">
      <table>
        <thead><tr><th>الكود</th><th>المعنى</th></tr></thead>
        <tbody>
          <tr><td><code>order.manage</code></td><td>إدارة الطلبات</td></tr>
        </tbody>
      </table>
    </div>

    <h3>8. صلاحيات الشركاء</h3>
    <div class="table-wrap">
      <table>
        <thead><tr><th>الكود</th><th>المعنى</th></tr></thead>
        <tbody>
          <tr><td><code>partner.manage</code></td><td>إدارة الوكلاء والفروع</td></tr>
        </tbody>
      </table>
    </div>

    <h3>9. صلاحيات الإنتاج</h3>
    <div class="table-wrap">
      <table>
        <thead><tr><th>الكود</th><th>المعنى</th></tr></thead>
        <tbody>
          <tr><td><code>production.manage</code></td><td>أوامر التصنيع</td></tr>
        </tbody>
      </table>
    </div>

    <h3>10. صلاحيات POS</h3>
    <div class="table-wrap">
      <table>
        <thead><tr><th>الكود</th><th>المعنى</th></tr></thead>
        <tbody>
          <tr><td><code>pos.sell</code></td><td>البيع</td></tr>
          <tr><td><code>pos.settle</code></td><td>التسوية</td></tr>
        </tbody>
      </table>
    </div>

    <h3>11. صلاحيات اللوجستيات</h3>
    <div class="table-wrap">
      <table>
        <thead><tr><th>الكود</th><th>المعنى</th></tr></thead>
        <tbody>
          <tr><td><code>logistics.manage</code></td><td>إدارة الشحنات</td></tr>
          <tr><td><code>logistics.deliver</code></td><td>تأكيد التسليم</td></tr>
        </tbody>
      </table>
    </div>

    <h3>12. صلاحيات التواصل</h3>
    <div class="table-wrap">
      <table>
        <thead><tr><th>الكود</th><th>المعنى</th></tr></thead>
        <tbody>
          <tr><td><code>comm.moderate</code></td><td>مراقبة الشات</td></tr>
        </tbody>
      </table>
    </div>

    <h3>13. صلاحيات عامة</h3>
    <div class="table-wrap">
      <table>
        <thead><tr><th>الكود</th><th>المعنى</th></tr></thead>
        <tbody>
          <tr><td><code>bi.view</code></td><td>لوحة التحليلات</td></tr>
          <tr><td><code>notify.send</code></td><td>إرسال إشعار</td></tr>
        </tbody>
      </table>
    </div>

    <!-- ==================== جدول الصلاحيات ==================== -->
    <h2 id="permissions-table" class="section">جدول الصلاحيات لكل دور</h2>

    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>الصلاحية</th>
            <th>admin.high</th>
            <th>admin</th>
            <th>staff</th>
            <th>supplier</th>
            <th>customer</th>
            <th>agent</th>
            <th>branch</th>
          </tr>
        </thead>
        <tbody>
          <tr><td><code>*</code></td><td>✅</td><td>❌</td><td>❌</td><td>❌</td><td>❌</td><td>❌</td><td>❌</td></tr>
          <tr><td><code>user.read</code></td><td>✅</td><td>✅</td><td>✅</td><td>❌</td><td>❌</td><td>❌</td><td>❌</td></tr>
          <tr><td><code>user.impersonate</code></td><td>✅</td><td>✅</td><td>✅</td><td>❌</td><td>❌</td><td>❌</td><td>❌</td></tr>
          <tr><td><code>supplier.approve</code></td><td>✅</td><td>✅</td><td>✅</td><td>❌</td><td>❌</td><td>❌</td><td>❌</td></tr>
          <tr><td><code>credit.manage</code></td><td>✅</td><td>✅</td><td>❌</td><td>❌</td><td>❌</td><td>❌</td><td>❌</td></tr>
          <tr><td><code>credit.override</code></td><td>✅</td><td>❌</td><td>❌</td><td>❌</td><td>❌</td><td>❌</td><td>❌</td></tr>
          <tr><td><code>payment.collect</code></td><td>✅</td><td>✅</td><td>✅</td><td>❌</td><td>❌</td><td>✅</td><td>✅</td></tr>
          <tr><td><code>payment.approve</code></td><td>✅</td><td>✅</td><td>❌</td><td>❌</td><td>❌</td><td>✅</td><td>✅</td></tr>
          <tr><td><code>period.close</code></td><td>✅</td><td>❌</td><td>❌</td><td>❌</td><td>❌</td><td>❌</td><td>❌</td></tr>
          <tr><td><code>high.manual_journal</code></td><td>✅</td><td>❌</td><td>❌</td><td>❌</td><td>❌</td><td>❌</td><td>❌</td></tr>
          <tr><td><code>product.manage</code></td><td>✅</td><td>✅</td><td>✅</td><td>❌</td><td>❌</td><td>❌</td><td>❌</td></tr>
          <tr><td><code>inventory.manage</code></td><td>✅</td><td>✅</td><td>✅</td><td>❌</td><td>❌</td><td>❌</td><td>❌</td></tr>
          <tr><td><code>offer.manage</code></td><td>❌</td><td>❌</td><td>❌</td><td>✅</td><td>❌</td><td>❌</td><td>❌</td></tr>
          <tr><td><code>shortage.resolve</code></td><td>✅</td><td>✅</td><td>❌</td><td>❌</td><td>❌</td><td>❌</td><td>❌</td></tr>
          <tr><td><code>order.manage</code></td><td>✅</td><td>✅</td><td>✅</td><td>❌</td><td>❌</td><td>❌</td><td>❌</td></tr>
          <tr><td><code>partner.manage</code></td><td>✅</td><td>✅</td><td>❌</td><td>❌</td><td>❌</td><td>❌</td><td>❌</td></tr>
          <tr><td><code>production.manage</code></td><td>✅</td><td>✅</td><td>✅</td><td>❌</td><td>❌</td><td>❌</td><td>❌</td></tr>
          <tr><td><code>pos.sell</code></td><td>✅</td><td>✅</td><td>✅</td><td>❌</td><td>❌</td><td>✅</td><td>✅</td></tr>
          <tr><td><code>pos.settle</code></td><td>✅</td><td>✅</td><td>❌</td><td>❌</td><td>❌</td><td>❌</td><td>❌</td></tr>
          <tr><td><code>logistics.manage</code></td><td>✅</td><td>✅</td><td>✅</td><td>❌</td><td>❌</td><td>❌</td><td>❌</td></tr>
          <tr><td><code>logistics.deliver</code></td><td>✅</td><td>✅</td><td>✅</td><td>❌</td><td>❌</td><td>❌</td><td>❌</td></tr>
          <tr><td><code>comm.moderate</code></td><td>✅</td><td>✅</td><td>❌</td><td>❌</td><td>❌</td><td>❌</td><td>❌</td></tr>
          <tr><td><code>bi.view</code></td><td>✅</td><td>✅</td><td>❌</td><td>❌</td><td>❌</td><td>❌</td><td>❌</td></tr>
          <tr><td><code>notify.send</code></td><td>✅</td><td>✅</td><td>❌</td><td>❌</td><td>❌</td><td>❌</td><td>❌</td></tr>
        </tbody>
      </table>
    </div>

    <!-- ==================== الفصل الأول ==================== -->
    <h2 id="ch1" class="section">الفصل الأول: البدء</h2>

    <h3>1.1 — كيف تدخل على النظام؟</h3>

    <div class="steps">
      <div class="step">
        <div class="step-title">افتح المتصفح</div>
        <div class="step-desc">Chrome أو Edge (يفضل Chrome).</div>
      </div>
      <div class="step">
        <div class="step-title">اكتب الرابط</div>
        <div class="step-desc"><code>https://whitemoon.manasety.ai</code></div>
      </div>
      <div class="step">
        <div class="step-title">اكتب بيانات الدخول</div>
        <div class="step-desc">البريد الإلكتروني وكلمة المرور.</div>
      </div>
      <div class="step">
        <div class="step-title">اضغط دخول</div>
        <div class="step-desc">لو أول مرة، هيطلب تغيير كلمة المرور.</div>
      </div>
    </div>

    <div class="callout warning">
      <div class="callout-icon">⚠️</div>
      <div class="callout-content">
        <div class="callout-title">ملاحظة</div>
        <p>لو أول مرة تدخل، هيطلب منك تغير كلمة المرور. اختار كلمة قوية (12 حرف على الأقل).</p>
      </div>
    </div>

    <h3>1.2 — كيف تغير كلمة المرور؟</h3>

    <div class="steps">
      <div class="step">
        <div class="step-title">اضغط الإعدادات</div>
        <div class="step-desc">من القائمة الجانبية.</div>
      </div>
      <div class="step">
        <div class="step-title">اختار تغيير كلمة المرور</div>
        <div class="step-desc">هتفتحلك شاشة التغيير.</div>
      </div>
      <div class="step">
        <div class="step-title">اكتب كلمات المرور</div>
        <div class="step-desc">الحالية + الجديدة + التأكيد.</div>
      </div>
      <div class="step">
        <div class="step-title">اضغط حفظ</div>
        <div class="step-desc">كلمة المرور بتتخزن مشفرة (Argon2).</div>
      </div>
    </div>

    <h3>1.3 — كيف تفعّل التحقق بخطوتين (2FA)؟</h3>

    <div class="steps">
      <div class="step">
        <div class="step-title">نزّل Google Authenticator</div>
        <div class="step-desc">أو Authy على موبايلك.</div>
      </div>
      <div class="step">
        <div class="step-title">اذهب لتفعيل 2FA</div>
        <div class="step-desc">القائمة الجانبية → الأمان → تفعيل 2FA.</div>
      </div>
      <div class="step">
        <div class="step-title">صوّر الـ QR Code</div>
        <div class="step-desc">افتح التطبيق، اضغط +، صوّر الـ QR.</div>
      </div>
      <div class="step">
        <div class="step-title">احفظ Backup Codes</div>
        <div class="step-desc">8 أكواد احتياطية — انسخها في مكان آمن.</div>
      </div>
      <div class="step">
        <div class="step-title">أكّد الكود</div>
        <div class="step-desc">اكتب كود التحقق من التطبيق.</div>
      </div>
    </div>

    <div class="callout danger">
      <div class="callout-icon">🔴</div>
      <div class="callout-content">
        <div class="callout-title">مهم جداً</div>
        <p>انسخ الأكواد في مكان آمن. كل كود يُستخدم مرة واحدة. لو الموبايل ضاع، دي طريقتك الوحيدة للدخول.</p>
      </div>
    </div>

    <!-- ==================== الفصل الثاني ==================== -->
    <h2 id="ch2" class="section">الفصل الثاني: إدارة المستخدمين</h2>

    <h3>2.1 — الشاشات الأربع</h3>

    <div class="table-wrap">
      <table>
        <thead><tr><th>#</th><th>الشاشة</th><th>الرابط</th></tr></thead>
        <tbody>
          <tr><td>1</td><td>قائمة المستخدمين</td><td><code>/admin/users</code></td></tr>
          <tr><td>2</td><td>تفاصيل مستخدم</td><td><code>/admin/users/:id</code></td></tr>
          <tr><td>3</td><td>الموردون المنتظرون</td><td><code>/admin/suppliers/pending</code></td></tr>
          <tr><td>4</td><td>Impersonation</td><td><code>/admin/impersonation</code></td></tr>
        </tbody>
      </table>
    </div>

    <h3>2.2 — عرض قائمة المستخدمين</h3>

    <p>الرابط: <code>https://whitemoon.manasety.ai/admin/users</code></p>

    <p>هتظهرلك جدول فيه:</p>

    <ul>
      <li><strong>ID</strong> — رقم المستخدم</li>
      <li><strong>Email/Phone</strong> — البريد أو الموبايل</li>
      <li><strong>النوع (kind)</strong> — admin / staff / customer / supplier / agent / branch</li>
      <li><strong>الحالة (status)</strong> — active / pending / suspended / locked</li>
      <li><strong>الأدوار</strong> — الدور أو الأدوار الممنوحة</li>
      <li><strong>تاريخ الإنشاء</strong></li>
    </ul>

    <h4>الحالات الأربعة</h4>

    <div class="table-wrap">
      <table>
        <thead><tr><th>الحالة</th><th>المعنى</th><th>متى تستخدمها</th></tr></thead>
        <tbody>
          <tr><td><span class="badge badge-warning">pending</span></td><td>مسجل بس ما اتأكدش</td><td>مورد لسه ما اتوافقش</td></tr>
          <tr><td><span class="badge badge-success">active</span></td><td>نشط</td><td>الحالة الطبيعية</td></tr>
          <tr><td><span class="badge badge-warning">suspended</span></td><td>موقوف مؤقتاً</td><td>مخالفة، شكوى</td></tr>
          <tr><td><span class="badge badge-danger">locked</span></td><td>مقفول نهائي</td><td>احتيال</td></tr>
        </tbody>
      </table>
    </div>

    <h3>2.3 — الموافقة على الموردين (KYC)</h3>

    <p>الرابط: <code>/admin/suppliers/pending</code></p>

    <h4>الـ Workflow</h4>

    <pre><code>المورد يسجل → pending → OTP → لسه pending
    ↓
يظهر في /admin/suppliers/pending
    ↓
الأدمن يراجع المستندات
    ↓
    ├── يوافق → active
    └── يرفض → rejected + سبب</code></pre>

    <div class="steps">
      <div class="step">
        <div class="step-title">اذهب للشاشة</div>
        <div class="step-desc">/admin/suppliers/pending</div>
      </div>
      <div class="step">
        <div class="step-title">اضغط على المورد</div>
        <div class="step-desc">هتفتحلك التفاصيل.</div>
      </div>
      <div class="step">
        <div class="step-title">راجع المستندات</div>
        <div class="step-desc">السجل التجاري، البطاقة الضريبية، الرقم القومي.</div>
      </div>
      <div class="step">
        <div class="step-title">اختر: Approve أو Reject</div>
        <div class="step-desc">لو Reject، اكتب السبب (إلزامي).</div>
      </div>
    </div>

    <h3>2.4 — Impersonation (View as)</h3>

    <p>الرابط: <code>/admin/impersonation</code></p>

    <p>تدخل كأنك مستخدم تاني — تشوف بعينه، تجرب مشاكله.</p>

    <div class="callout warning">
      <div class="callout-icon">⚠️</div>
      <div class="callout-content">
        <div class="callout-title">تحذير</div>
        <p>كل Impersonation بيتسجل في <code>audit.events</code>. مسموح للـ admin.high و admin فقط. لازم تكتب سبب إلزامي.</p>
      </div>
    </div>

    <!-- ==================== الفصل الثالث ==================== -->
    <h2 id="ch3" class="section">الفصل الثالث: سجل التدقيق (Audit Log)</h2>

    <p>الرابط: <code>/admin/audit</code></p>
    <p>الصلاحية: <strong>admin.high فقط</strong></p>

    <div class="callout info">
      <div class="callout-icon">💡</div>
      <div class="callout-content">
        <div class="callout-title">القاعدة الأساسية</div>
        <p><code>audit.events</code> جدول إضافي فقط (Append-only): تسجيل ✅، قراءة ✅، تعديل ❌، حذف ❌.</p>
      </div>
    </div>

    <h3>3.1 — إيه اللي بيتسجل؟</h3>

    <h4>أحداث المصادقة</h4>
    <div class="table-wrap">
      <table>
        <thead><tr><th>الحدث</th><th>معناه</th></tr></thead>
        <tbody>
          <tr><td><code>user.register</code></td><td>عميل جديد</td></tr>
          <tr><td><code>supplier.register</code></td><td>مورد جديد</td></tr>
          <tr><td><code>user.otp.verify</code></td><td>تأكيد OTP</td></tr>
          <tr><td><code>user.login</code></td><td>دخول</td></tr>
          <tr><td><code>user.logout</code></td><td>خروج</td></tr>
        </tbody>
      </table>
    </div>

    <h4>أحداث إدارة المستخدمين</h4>
    <div class="table-wrap">
      <table>
        <thead><tr><th>الحدث</th><th>معناه</th></tr></thead>
        <tbody>
          <tr><td><code>supplier.approve</code></td><td>الموافقة على مورد</td></tr>
          <tr><td><code>supplier.reject</code></td><td>رفض مورد</td></tr>
          <tr><td><code>user.impersonate.start</code></td><td>بداية Impersonation</td></tr>
          <tr><td><code>user.impersonate.stop</code></td><td>نهاية Impersonation</td></tr>
          <tr><td><code>user.suspend</code></td><td>تعليق</td></tr>
          <tr><td><code>user.activate</code></td><td>تنشيط</td></tr>
        </tbody>
      </table>
    </div>

    <h4>أحداث المحاسبة</h4>
    <div class="table-wrap">
      <table>
        <thead><tr><th>الحدث</th><th>معناه</th></tr></thead>
        <tbody>
          <tr><td><code>period.close</code></td><td>إغلاق فترة</td></tr>
          <tr><td><code>period.reopen</code></td><td>فتح فترة</td></tr>
          <tr><td><code>journal.post.manual</code></td><td>قيد يدوي</td></tr>
          <tr><td><code>journal.post.closed_period</code></td><td>قيد على فترة مقفولة</td></tr>
        </tbody>
      </table>
    </div>

    <h4>أحداث الائتمان</h4>
    <div class="table-wrap">
      <table>
        <thead><tr><th>الحدث</th><th>معناه</th></tr></thead>
        <tbody>
          <tr><td><code>credit.override</code></td><td>تجاوز سقف</td></tr>
          <tr><td><code>credit.tier.change</code></td><td>تغيير تصنيف</td></tr>
        </tbody>
      </table>
    </div>

    <!-- ==================== الفصل الرابع ==================== -->
    <h2 id="ch4" class="section">الفصل الرابع: المحاسبة والتقارير</h2>

    <div class="callout info">
      <div class="callout-icon">💡</div>
      <div class="callout-content">
        <div class="callout-title">المبدأ الأساسي</div>
        <p><strong>مفيش قيد بدون حدث، ومفيش حدث بدون قيد.</strong></p>
      </div>
    </div>

    <h3>4.1 — الشاشات المتاحة</h3>

    <div class="table-wrap">
      <table>
        <thead><tr><th>#</th><th>الشاشة</th><th>الرابط</th></tr></thead>
        <tbody>
          <tr><td>1</td><td>شجرة الحسابات</td><td><code>/accounting/chart</code></td></tr>
          <tr><td>2</td><td>الفترات</td><td><code>/accounting/periods</code></td></tr>
          <tr><td>3</td><td>قيد يدوي</td><td><code>/accounting/journal/manual</code></td></tr>
          <tr><td>4</td><td>الإيصالات</td><td><code>/accounting/receipts</code></td></tr>
          <tr><td>5</td><td>البيع الآجل</td><td><code>/accounting/deferred</code></td></tr>
          <tr><td>6</td><td>التقارير</td><td><code>/accounting/reports</code></td></tr>
        </tbody>
      </table>
    </div>

    <h3>4.2 — الفترات المحاسبية</h3>

    <p>الرابط: <code>/accounting/periods</code></p>

    <div class="callout warning">
      <div class="callout-icon">⚠️</div>
      <div class="callout-content">
        <div class="callout-title">القاعدة الذهبية</div>
        <p>بمجرد ما تقفل فترة، مفيش أي قيد جديد عليها. ده محمي بـ Database Trigger.</p>
      </div>
    </div>

    <h3>4.3 — التقارير الخمسة</h3>

    <div class="table-wrap">
      <table>
        <thead><tr><th>#</th><th>التقرير</th><th>الرابط</th></tr></thead>
        <tbody>
          <tr><td>1</td><td>ميزان المراجعة</td><td><code>/accounting/reports/trial-balance</code></td></tr>
          <tr><td>2</td><td>قائمة الدخل</td><td><code>/accounting/reports/income-statement</code></td></tr>
          <tr><td>3</td><td>الميزانية العمومية</td><td><code>/accounting/reports/balance-sheet</code></td></tr>
          <tr><td>4</td><td>التدفق النقدي</td><td><code>/accounting/reports/cash-flow</code></td></tr>
          <tr><td>5</td><td>دفتر الأستاذ</td><td><code>/accounting/reports/general-ledger</code></td></tr>
        </tbody>
      </table>
    </div>

    <!-- ==================== الفصل الخامس ==================== -->
    <h2 id="ch5" class="section">الفصل الخامس: المخازن والمنتجات</h2>

    <h3>5.1 — الشاشات</h3>

    <div class="table-wrap">
      <table>
        <thead><tr><th>#</th><th>الشاشة</th><th>الرابط</th></tr></thead>
        <tbody>
          <tr><td>1</td><td>الفئات</td><td><code>/inventory/categories</code></td></tr>
          <tr><td>2</td><td>المنتجات</td><td><code>/inventory/products</code></td></tr>
          <tr><td>3</td><td>الأرصدة</td><td><code>/inventory/stock</code></td></tr>
          <tr><td>4</td><td>التحويلات</td><td><code>/inventory/transfers</code></td></tr>
          <tr><td>5</td><td>النواقص</td><td><code>/inventory/shortages</code></td></tr>
          <tr><td>6</td><td>إعادة الطلب</td><td><code>/inventory/reorder</code></td></tr>
        </tbody>
      </table>
    </div>

    <h3>5.2 — الفرق بين المنتج وعرض المورد</h3>

    <pre><code>منتج → وصف عام: "أرز مصري 1 كجم"
    ↓
عرض المورد → مورد A: 25، B: 27، C: 24</code></pre>

    <div class="callout info">
      <div class="callout-icon">💡</div>
      <div class="callout-content">
        <div class="callout-title">ملاحظة مهمة</div>
        <p>المنتج واحد، العروض متعددة. العميل بيشوف أفضل سعر تلقائياً.</p>
      </div>
    </div>

    <!-- ==================== الفصل السادس ==================== -->
    <h2 id="ch6" class="section">الفصل السادس: الائتمان والتحصيل</h2>

    <h3>6.1 — التصنيف الائتماني</h3>

    <div class="table-wrap">
      <table>
        <thead>
          <tr><th>اللون</th><th>الكود</th><th>المعنى</th><th>السقف</th><th>% الآجل</th></tr>
        </thead>
        <tbody>
          <tr><td>أبيض</td><td><code>white</code></td><td>عميل جديد</td><td>250,000</td><td>60%</td></tr>
          <tr><td>أخضر</td><td><code>green</code></td><td>ملتزم</td><td>500,000</td><td>100%</td></tr>
          <tr><td>أصفر</td><td><code>yellow</code></td><td>إشارات تأخر</td><td>100,000</td><td>40%</td></tr>
          <tr><td>أحمر</td><td><code>red</code></td><td>مخاطرة</td><td>0</td><td>0%</td></tr>
        </tbody>
      </table>
    </div>

    <h3>6.2 — المستويات الخمسة للتصعيد</h3>

    <div class="table-wrap">
      <table>
        <thead>
          <tr><th>المستوى</th><th>الزناد</th><th>الإجراء</th><th>آلي؟</th></tr>
        </thead>
        <tbody>
          <tr><td>1</td><td>تأخر 1-7 أيام</td><td>SMS + واتساب + بريد</td><td>✅</td></tr>
          <tr><td>2</td><td>تأخر 8-15 يوم</td><td>تخفيض السقف 50%</td><td>✅</td></tr>
          <tr><td>3</td><td>تأخر 16-30 يوم</td><td>تنزيل درجة لونية</td><td>✅</td></tr>
          <tr><td>4</td><td>تأخر 31-60 يوم</td><td>تجميد الطلبات</td><td>✅</td></tr>
          <tr><td>5</td><td>تأخر > 60 يوم</td><td>تجميد كامل</td><td>❌ يدوي</td></tr>
        </tbody>
      </table>
    </div>

    <!-- ==================== الفصل السابع ==================== -->
    <h2 id="ch7" class="section">الفصل السابع: العمليات</h2>

    <h3>7.1 — دورة حياة الطلب</h3>

    <pre><code>1. العميل يتصفح الكتالوج
2. يضيف منتجات للسلة
3. يراجع السلة
4. يضغط Checkout
5. النظام يعمل Credit Check
6. الطلب يتقسم لـ Sub-orders (لكل مورد)
7. المخزون يُحجز
8. الأدمن يؤكد
9. الطلب يُجهّز
10. يُشحن
11. يُسلّم
12. الفاتورة تُصدر
13. التصنيف يُحدّث</code></pre>

    <div class="callout info">
      <div class="callout-icon">💡</div>
      <div class="callout-content">
        <div class="callout-title">ملاحظة مهمة</div>
        <p>العميل بيشوف طلب واحد بس، حتى لو الطلب مقسم لموردين كتير.</p>
      </div>
    </div>

    <h3>7.2 — حالات الطلب</h3>

    <div class="table-wrap">
      <table>
        <thead><tr><th>الحالة</th><th>المعنى</th></tr></thead>
        <tbody>
          <tr><td><span class="badge badge-warning">pending</span></td><td>جديد</td></tr>
          <tr><td><span class="badge badge-info">confirmed</span></td><td>مؤكد</td></tr>
          <tr><td><span class="badge badge-info">preparing</span></td><td>قيد التجهيز</td></tr>
          <tr><td><span class="badge badge-info">ready</span></td><td>جاهز للشحن</td></tr>
          <tr><td><span class="badge badge-accent">in_transit</span></td><td>في الطريق</td></tr>
          <tr><td><span class="badge badge-success">delivered</span></td><td>تم التسليم</td></tr>
          <tr><td><span class="badge badge-danger">cancelled</span></td><td>ملغي</td></tr>
          <tr><td><span class="badge badge-warning">returned</span></td><td>مرتجع</td></tr>
        </tbody>
      </table>
    </div>

    <!-- ==================== الفصل الثامن ==================== -->
    <h2 id="ch8" class="section">الفصل الثامن: الإنتاج والشركاء</h2>

    <h3>8.1 — أوامر التصنيع</h3>

    <p>الرابط: <code>/production</code></p>

    <p>تحويل <strong>مواد خام</strong> إلى <strong>منتج نهائي</strong>.</p>

    <h3>8.2 — الشركاء</h3>

    <p>الرابط: <code>/partners</code></p>

    <div class="table-wrap">
      <table>
        <thead>
          <tr><th></th><th>الوكيل</th><th>الفرع</th></tr>
        </thead>
        <tbody>
          <tr><td>الملكية</td><td>مستقل</td><td>تابع للشركة</td></tr>
          <tr><td>التأمين</td><td>مطلوب</td><td>غير مطلوب</td></tr>
          <tr><td>العمولة</td><td>يحصل عليها</td><td>لا</td></tr>
          <tr><td>العائد الاستثماري</td><td>نعم</td><td>لا</td></tr>
          <tr><td>POS</td><td>نعم</td><td>نعم</td></tr>
        </tbody>
      </table>
    </div>

    <!-- ==================== الفصل التاسع ==================== -->
    <h2 id="ch9" class="section">الفصل التاسع: الصيانة والمراقبة</h2>

    <div class="callout warning">
      <div class="callout-icon">⚠️</div>
      <div class="callout-content">
        <div class="callout-title">تحذير</div>
        <p>الفصل ده للمهندسين التقنيين فقط. متعملش أي حاجة من غير استشارة.</p>
      </div>
    </div>

    <h3>9.1 — البنية التحتية</h3>

    <div class="table-wrap">
      <table>
        <thead><tr><th>البند</th><th>القيمة</th></tr></thead>
        <tbody>
          <tr><td>الاستضافة</td><td>Hetzner</td></tr>
          <tr><td>IP</td><td>46.225.71.21</td></tr>
          <tr><td>نظام التشغيل</td><td>Ubuntu 24.04</td></tr>
          <tr><td>الدومين</td><td>whitemoon.manasety.ai</td></tr>
        </tbody>
      </table>
    </div>

    <h3>9.2 — Backup</h3>

    <pre><code># نسخة كاملة
sudo -u postgres pg_dump whitemoon | gzip > /root/backups/whitemoon_$(date +%Y%m%d).sql.gz</code></pre>

    <h3>9.3 — Monitoring</h3>

    <pre><code># حالة الخدمة
systemctl status whitemoon.service

# الـ Logs
journalctl -u whitemoon.service -n 50

# الأداء
free -h
df -h</code></pre>

    <!-- ==================== الفصل العاشر ==================== -->
    <h2 id="ch10" class="section">الفصل العاشر: الأسئلة الشائعة</h2>

    <h3>🔐 الدخول والحساب</h3>

    <h4>س1: نسيت كلمة المرور، أعمل إيه؟</h4>
    <p>لو عندك admin.high تاني → ادخل بيه واعمل reset. لو إنت الوحيد → كلم الدعم التقني.</p>

    <h4>س2: موبايلي ضاع، مش قادر أدخل بسبب 2FA؟</h4>
    <p>استخدم أحد الـ 8 Backup Codes اللي حفظتها وقت التفعيل. كل كود يُستخدم مرة واحدة.</p>

    <h4>س3: ليه النظام بيطلب مني كود من التطبيق كل مرة؟</h4>
    <p>ده 2FA — طبقة أمان إضافية. مقصود إنه يطلب كود كل دخول.</p>

    <h3>👥 المستخدمين</h3>

    <h4>س4: عايز أضيف موظف جديد، أعمل إيه؟</h4>
    <p>روح <code>/admin/users</code>. لو الزر "إضافة مستخدم" موجود → استخدمه. لو مش موجود → كلم الدعم التقني.</p>

    <h4>س5: موظف ساب الشركة، ينفع أحذفه؟</h4>
    <p>لأ — الحذف ممنوع لأسباب محاسبية. استخدم <strong>Suspend</strong> بدل الحذف.</p>

    <h4>س6: إزاي أعرف مين عدّل بياناتي؟</h4>
    <p>روح <code>/admin/audit</code> → فلتر <code>user.update</code> → Target = رقمك.</p>

    <h3>💰 المحاسبة</h3>

    <h4>س7: الفرق بين قيد تلقائي ويدوي؟</h4>
    <p>تلقائي من حدث (95%). يدوي استثنائي (5%).</p>

    <h4>س8: قفلت فترة بالغلط؟</h4>
    <p>admin.high فقط يقدر يفتحها. هيتسجل في Audit.</p>

    <h4>س9: عايز قيد على فترة مقفولة؟</h4>
    <p>محتاج <code>high.manual_journal.closed_period</code>. متستخدمهاش غير للضرورة.</p>

    <h3>📦 المخازن</h3>

    <h4>س10: الفرق بين المنتج وعرض المورد؟</h4>
    <p>المنتج وصف عام ("أرز مصري 1 كجم"). العروض أسعار موردين. المنتج واحد، العروض متعددة.</p>

    <h4>س11: إزاي أنقل بضاعة لوكيل؟</h4>
    <p>روح <code>/inventory/transfers</code> → إذن جديد.</p>

    <h3>💳 الائتمان</h3>

    <h4>س12: عميل عايز يشتري آجل؟</h4>
    <p>النظام يتعامل تلقائي. لو داخل السقف → يمشي. لو تجاوز → رفض.</p>

    <h4>س13: عميل اتأخر؟</h4>
    <p>النظام يصعّد تلقائي (1-4). المستوى 5 يدوي.</p>

    <h4>س14: عميل في "أحمر"؟</h4>
    <p>نقدي فقط. الاستثناء admin.high بـ <code>credit.override</code>.</p>

    <h3>📦 الطلبات</h3>

    <h4>س15: عميل عايز يلغي طلب؟</h4>
    <p>قبل الشحن → إلغاء عادي. بعد الشحن → مرتجع.</p>

    <h4>س16: إيه هو RFQ؟</h4>
    <p>Request for Quotation — طلب عرض سعر. الموردين يقدموا، العميل يختار.</p>

    <h4>س17: هوية المورد بتظهر للعميل في RFQ؟</h4>
    <p>لأ — قاعدة Non-negotiable. العميل يشوف السعر والمواصفات بس.</p>

    <!-- ==================== الملاحق ==================== -->
    <h2 id="appendix-a" class="section">الملحق أ: جدول الصلاحيات الكامل</h2>

    <p>راجع <a href="#permissions-table">جدول الصلاحيات لكل دور</a> في القسم التمهيدي.</p>

    <h2 id="appendix-b" class="section">الملحق ب: جدول المسارات الكامل</h2>

    <div class="table-wrap">
      <table>
        <thead><tr><th>المسار</th><th>الشاشة</th><th>من يستخدمها</th></tr></thead>
        <tbody>
          <tr><td><code>/login</code></td><td>تسجيل دخول</td><td>الجميع</td></tr>
          <tr><td><code>/register</code></td><td>تسجيل عميل</td><td>الجميع</td></tr>
          <tr><td><code>/register/supplier</code></td><td>تسجيل مورد</td><td>الجميع</td></tr>
          <tr><td><code>/otp</code></td><td>تأكيد OTP</td><td>الجميع</td></tr>
          <tr><td><code>/</code></td><td>الرئيسية</td><td>الجميع</td></tr>
          <tr><td><code>/catalog</code></td><td>الكتالوج</td><td>الجميع</td></tr>
          <tr><td><code>/cart</code></td><td>السلة</td><td>الجميع</td></tr>
          <tr><td><code>/orders</code></td><td>الطلبات</td><td>الجميع</td></tr>
          <tr><td><code>/rfq</code></td><td>RFQ</td><td>الجميع</td></tr>
          <tr><td><code>/statement</code></td><td>كشف حساب</td><td>الجميع</td></tr>
          <tr><td><code>/chat</code></td><td>الشات</td><td>الجميع</td></tr>
          <tr><td><code>/admin/users</code></td><td>المستخدمون</td><td>FINANCE</td></tr>
          <tr><td><code>/admin/suppliers/pending</code></td><td>موردون منتظرون</td><td>FINANCE</td></tr>
          <tr><td><code>/admin/impersonation</code></td><td>Impersonation</td><td>FINANCE</td></tr>
          <tr><td><code>/admin/audit</code></td><td>Audit Log</td><td>admin.high</td></tr>
          <tr><td><code>/accounting/chart</code></td><td>شجرة الحسابات</td><td>FINANCE</td></tr>
          <tr><td><code>/accounting/periods</code></td><td>الفترات</td><td>FINANCE</td></tr>
          <tr><td><code>/accounting/reports/*</code></td><td>التقارير</td><td>FINANCE</td></tr>
          <tr><td><code>/credit</code></td><td>الائتمان</td><td>FINANCE</td></tr>
          <tr><td><code>/credit/dunning</code></td><td>التصعيد</td><td>FINANCE</td></tr>
          <tr><td><code>/partners</code></td><td>الشركاء</td><td>FINANCE</td></tr>
          <tr><td><code>/production</code></td><td>الإنتاج</td><td>FINANCE</td></tr>
          <tr><td><code>/pos</code></td><td>POS</td><td>agent/branch/staff/admin</td></tr>
          <tr><td><code>/logistics/*</code></td><td>اللوجستيات</td><td>FINANCE</td></tr>
          <tr><td><code>/dashboard</code></td><td>BI Dashboard</td><td>FINANCE</td></tr>
        </tbody>
      </table>
    </div>

    <h2 id="appendix-c" class="section">الملحق ج: معلومات الاتصال</h2>

    <h3>الدعم التقني</h3>
    <ul>
      <li><strong>البريد:</strong> support@manasety.ai</li>
      <li><strong>الهاتف:</strong> (اطلب من الإدارة)</li>
      <li><strong>ساعات العمل:</strong> 9 ص - 6 م (الأحد-الخميس)</li>
    </ul>

    <h3>في حالة الطوارئ</h3>
    <ol>
      <li>جرب تاني بعد 5 دقايق</li>
      <li>جرب متصفح تاني</li>
      <li>كلم الدعم: emergency@manasety.ai</li>
      <li>جهّز: إيه اللي كنت بتعمله، رسالة الخطأ، متى</li>
    </ol>

    <h3>جهات داخلية</h3>
    <div class="table-wrap">
      <table>
        <thead><tr><th>الدور</th><th>المسؤول</th></tr></thead>
        <tbody>
          <tr><td>المدير المالي</td><td>م. عبد الحميد شلبي</td></tr>
          <tr><td>مدير المشروع</td><td>(أنت)</td></tr>
          <tr><td>ممثل العميل</td><td>أ. مسعود مهران / أ. أحمد رشاد</td></tr>
        </tbody>
      </table>
    </div>

    <h2 id="appendix-d" class="section">الملحق د: قاموس المصطلحات</h2>

    <div class="table-wrap">
      <table>
        <thead><tr><th>المصطلح</th><th>المعنى</th></tr></thead>
        <tbody>
          <tr><td>RFQ</td><td>Request for Quotation — طلب عرض سعر</td></tr>
          <tr><td>MOQ</td><td>Minimum Order Quantity — الحد الأدنى للطلب</td></tr>
          <tr><td>KYC</td><td>Know Your Customer — التحقق من العميل</td></tr>
          <tr><td>POS</td><td>Point of Sale — نقطة بيع</td></tr>
          <tr><td>MO</td><td>Manufacturing Order — أمر تصنيع</td></tr>
          <tr><td>OTP</td><td>One-Time Password — كلمة مرور لمرة واحدة</td></tr>
          <tr><td>2FA</td><td>Two-Factor Authentication — تحقق بخطوتين</td></tr>
          <tr><td>TOTP</td><td>Time-based OTP — OTP زمني</td></tr>
          <tr><td>JWT</td><td>JSON Web Token — توكن الدخول</td></tr>
          <tr><td>RBAC</td><td>Role-Based Access Control — التحكم بالأدوار</td></tr>
          <tr><td>OCR</td><td>Optical Character Recognition — التعرف الضوئي</td></tr>
          <tr><td>FIFO</td><td>First In First Out — الأقدم أولاً</td></tr>
          <tr><td>ETA</td><td>Egyptian Tax Authority — مصلحة الضرائب</td></tr>
          <tr><td>COA</td><td>Chart of Accounts — شجرة الحسابات</td></tr>
          <tr><td>GL</td><td>General Ledger — دفتر الأستاذ</td></tr>
          <tr><td>P&L</td><td>Profit & Loss — الأرباح والخسائر</td></tr>
          <tr><td>BS</td><td>Balance Sheet — الميزانية العمومية</td></tr>
          <tr><td>CF</td><td>Cash Flow — التدفق النقدي</td></tr>
          <tr><td>TB</td><td>Trial Balance — ميزان المراجعة</td></tr>
          <tr><td>SLA</td><td>Service Level Agreement — اتفاقية مستوى الخدمة</td></tr>
          <tr><td>DR</td><td>Disaster Recovery — التعافي من الكوارث</td></tr>
        </tbody>
      </table>
    </div>
`

export function UserGuidePage() {
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState('intro-section')
  const [progress, setProgress] = useState(0)

  useEffect(() => {
    const ids = TOC.flatMap((g) => g.items.map((i) => i.id))
    const obs = new IntersectionObserver(
      (entries) => {
        for (const e of entries) if (e.isIntersecting) setActive(e.target.id)
      },
      { rootMargin: '-84px 0px -70% 0px', threshold: 0 },
    )
    for (const id of ids) {
      const el = document.getElementById(id)
      if (el) obs.observe(el)
    }
    return () => obs.disconnect()
  }, [])

  useEffect(() => {
    const onScroll = () => {
      const el = document.documentElement
      const max = el.scrollHeight - el.clientHeight
      setProgress(max > 0 ? (el.scrollTop / max) * 100 : 0)
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    onScroll()
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  const Toc = ({ onNavigate }: { onNavigate?: () => void }) => (
    <nav className="flex flex-col gap-space-md">
      {TOC.map((g) => (
        <div key={g.group} className="flex flex-col gap-space-xs">
          <span className="px-space-sm font-small-medium text-small-medium text-tertiary">{g.group}</span>
          {g.items.map((it) => {
            const on = active === it.id
            return (
              <a
                key={it.id}
                href={`#${it.id}`}
                onClick={onNavigate}
                className={`flex items-center gap-space-sm rounded-lg px-space-sm py-[7px] font-small-medium text-small-medium transition-colors ${
                  on
                    ? 'bg-brand-weak text-primary'
                    : 'text-on-surface-variant hover:bg-surface-container-low hover:text-primary'
                }`}
              >
                <Icon name={it.icon} size={18} className={on ? 'text-primary' : 'text-secondary'} />
                <span className="truncate">{it.label}</span>
              </a>
            )
          })}
        </div>
      ))}
    </nav>
  )

  return (
    <div dir="rtl" className="min-h-screen bg-background text-on-surface font-body">
      <style>{GUIDE_STYLES}</style>

      {/* reading progress */}
      <div className="guide-no-print fixed inset-x-0 top-0 z-50 h-1 bg-transparent">
        <div className="h-full bg-tertiary transition-[width] duration-150" style={{ width: `${progress}%` }} />
      </div>

      {/* top bar */}
      <header className="guide-no-print sticky top-0 z-40 border-b border-surface-container-high bg-background/85 backdrop-blur">
        <div className="mx-auto flex max-w-[1200px] items-center justify-between gap-space-md px-gutter py-space-sm">
          <div className="flex items-center gap-space-md">
            <button
              type="button"
              onClick={() => setOpen((o) => !o)}
              aria-label="فهرس الدليل"
              className="grid h-9 w-9 place-items-center rounded-lg border border-surface-container-high text-primary lg:hidden"
            >
              <Icon name={open ? 'close' : 'menu'} size={20} />
            </button>
            <Brand size={26} />
            <span className="hidden font-small text-small text-on-surface-variant sm:block">دليل الاستخدام</span>
          </div>
          <div className="flex items-center gap-space-sm">
            <Button onClick={() => window.print()} iconRight="print">
              <span className="hidden sm:inline">طباعة</span>
            </Button>
            <Link to="/home">
              <Button variant="primary" iconRight="arrow_back">
                <span className="hidden sm:inline">لوحة التحكم</span>
              </Button>
            </Link>
          </div>
        </div>
      </header>

      {/* mobile drawer */}
      {open && (
        <>
          <div className="guide-no-print fixed inset-0 z-30 bg-inverse-surface/30 lg:hidden" onClick={() => setOpen(false)} />
          <aside className="guide-no-print fixed inset-y-0 right-0 z-40 w-[280px] overflow-y-auto border-l border-surface-container-high bg-surface-container-lowest p-space-lg pt-[76px] shadow-overlay lg:hidden">
            <Toc onNavigate={() => setOpen(false)} />
          </aside>
        </>
      )}

      <div className="mx-auto flex max-w-[1200px] gap-space-xl px-gutter">
        {/* desktop TOC */}
        <aside className="guide-no-print sticky top-[64px] hidden h-[calc(100vh-64px)] w-[256px] shrink-0 overflow-y-auto py-space-xl lg:block">
          <Toc />
        </aside>

        {/* content */}
        <main className="min-w-0 flex-1 py-space-xl">
          <section
            id="intro"
            className="relative overflow-hidden rounded-2xl bg-primary px-space-lg py-10 text-on-primary shadow-card md:px-12 md:py-14"
          >
            <div aria-hidden className="pointer-events-none absolute -left-16 -top-16 h-56 w-56 rounded-full bg-tertiary/20 blur-3xl" />
            <div className="relative">
              <span className="inline-flex items-center gap-space-xs rounded-pill bg-tertiary/20 px-space-md py-space-xs font-small-medium text-small-medium text-tertiary-fixed">
                <Icon name="auto_stories" size={16} /> الإصدار 1.0 · أكتوبر 2026
              </span>
              <h1 className="mt-space-md font-display text-[30px] font-semibold tracking-tight md:text-[40px]">دليل استخدام وايت مون</h1>
              <p className="mt-space-sm max-w-2xl font-body text-body text-on-primary/80 md:text-[16px]">
                دليل شامل لإدارة المنظومة المتكاملة — B2B Marketplace + ERP
              </p>
              <div className="mt-space-lg flex flex-wrap gap-x-space-xl gap-y-space-sm font-small-medium text-small-medium text-on-primary/75">
                <span className="inline-flex items-center gap-space-xs"><Icon name="menu_book" size={16} className="text-tertiary-fixed-dim" /> ١٠ فصول</span>
                <span className="inline-flex items-center gap-space-xs"><Icon name="groups" size={16} className="text-tertiary-fixed-dim" /> ٧ أدوار</span>
                <span className="inline-flex items-center gap-space-xs"><Icon name="key" size={16} className="text-tertiary-fixed-dim" /> ٣٣ صلاحية</span>
                <span className="inline-flex items-center gap-space-xs"><Icon name="table_chart" size={16} className="text-tertiary-fixed-dim" /> +٤٥ جدول</span>
              </div>
            </div>
          </section>

          <article className="guide-prose mt-space-md" dangerouslySetInnerHTML={{ __html: GUIDE_HTML }} />

          <footer className="mt-space-xl rounded-2xl border border-surface-container-high bg-surface-container-low p-space-lg text-center">
            <p className="font-headline-2 text-headline-2 text-primary">دليل استخدام وايت مون</p>
            <p className="mt-space-xs font-small text-small text-on-surface-variant">الإصدار 1.0 · أكتوبر 2026 · © جميع الحقوق محفوظة — فريق وايت مون</p>
            <div className="mt-space-md flex flex-wrap items-center justify-center gap-space-md font-small-medium text-small-medium">
              <a href="#intro" className="text-secondary hover:text-primary">الرئيسية</a>
              <span className="text-outline-variant">·</span>
              <a href="#ch1" className="text-secondary hover:text-primary">البدء</a>
              <span className="text-outline-variant">·</span>
              <a href="#ch10" className="text-secondary hover:text-primary">الأسئلة الشائعة</a>
              <span className="text-outline-variant">·</span>
              <a href="https://whitemoon.manasety.ai" target="_blank" rel="noreferrer" className="text-secondary hover:text-primary">المنظومة</a>
            </div>
          </footer>
        </main>
      </div>
    </div>
  )
}
