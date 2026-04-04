#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🌐 Proxy Store Bot — نسخة v4 نهائية
✅ مخزن رقمي | ✅ خصومات يدوية | ✅ أزرار تعمل من أي مكان
"""

import logging
import json
import os
import psycopg2
import psycopg2.extras
import requests
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

# ============================================================
# ⚙️  CONFIGURATION
# ============================================================
BOT_TOKEN        = os.getenv("BOT_TOKEN", "8678179663:AAF0XHqXkf8_ZjI4_0ypY6WfnJKogr7Xk4s")
ADMIN_IDS        = [7286057617]
STORE_NAME       = "🌐 Proxy Store"
CURRENCY         = "USDT"
SUPPORT_USERNAME = "@m_issam_31"
DATABASE_URL     = os.getenv("DATABASE_URL", "")   # ← ضع رابط قاعدة البيانات هنا أو في env
STOCK_LOW_ALERT  = 5
HELEKET_MERCHANT_ID  = os.getenv("HELEKET_MERCHANT_ID", "YOUR_MERCHANT_UUID")
HELEKET_API_KEY      = os.getenv("HELEKET_API_KEY",     "YOUR_PAYMENT_API_KEY")
HELEKET_CALLBACK_URL = os.getenv("HELEKET_CALLBACK_URL","")
BINANCE_PAY_ID       = os.getenv("BINANCE_PAY_ID",      "YOUR_BINANCE_PAY_ID")
MIN_DEPOSIT          = 1.0

# ============================================================
# 📖  TRANSLATIONS  (ar / en / fr)
# ============================================================
TR = {
"ar": {
    "choose_lang":       "🌐 اختر لغتك:",
    "main_menu":         "🏠 القائمة الرئيسية\nأهلاً {name}!",
    "browse":            "🛍️ تصفح المنتجات",
    "cart":              "🛒 السلة ({n})",
    "my_orders":         "📦 طلباتي",
    "wallet":            "💰 محفظتي",
    "support":           "💬 الدعم",
    "settings":          "⚙️ الإعدادات",
    "admin":             "👑 لوحة التحكم",
    "back":              "◀️ رجوع",
    "back_main":         "🏠 القائمة",
    "back_admin":        "◀️ لوحة التحكم",
    "add_cart":          "🛒 أضف للسلة",
    "buy_now":           "⚡ اشتري الآن",
    "available":         "✅ متوفر",
    "unlimited":         "∞ غير محدود",
    "out_of_stock":      "❌ نفد المخزون",
    "cart_empty":        "🛒 سلتك فارغة",
    "total":             "💰 الإجمالي",
    "checkout":          "✅ إتمام الشراء",
    "clear_cart":        "🗑️ تفريغ السلة",
    "pay_title":         "💳 اختر طريقة الدفع:",
    "pay_wallet":        "💰 من المحفظة ({b} USDT)",
    "pay_manual":        "📸 تحويل بنكي / USDT",
    "pay_crypto":        "₿ CryptoPay",
    "no_balance":        "❌ رصيد غير كافٍ\nرصيدك: {b} USDT",
    "order_done":        "✅ طلب #{id} تم بنجاح!",
    "send_receipt":      "📸 أرسل صورة الإيصال\n\n💳 USDT (TRC20):\nTYourAddressHere",
    "receipt_recv":      "✅ استلمنا الإيصال! سيتم المراجعة قريباً",
    "order_rejected":    "❌ تم رفض طلب #{id}\nتواصل مع الدعم",
    "no_orders":         "📦 لا توجد طلبات بعد",
    "order_item":        "#{id} | {total} USDT | {status} | {date}",
    "pending":           "⏳ قيد المراجعة",
    "completed":         "✅ مكتمل",
    "cancelled":         "❌ ملغي",
    "wallet_info":       "💰 رصيدك: {b} USDT",
    "deposit":           "💳 إيداع رصيد",
    "deposit_amount":    "💵 أدخل المبلغ بالـ USDT (أقل مبلغ {min}):",
    "deposit_link":      "🔗 رابط الدفع جاهز!\n\n💰 المبلغ: {amount} USDT\n⏳ صالح لـ 20 دقيقة\n\nاضغط الزر أدناه للدفع:",
    "deposit_invalid":   "❌ أدخل رقماً صحيحاً (أقل مبلغ {min} USDT)",
    "deposit_done":      "✅ تم إضافة {amount} USDT لرصيدك!\nرصيدك الآن: {balance} USDT",
    "pay_heleket":       "₿ Heleket (كريبتو)",
    "pay_binance":       "🟡 Binance Pay",
    "send_binance_id":   "📋 حوّل {amount} USDT إلى Binance Pay ID:\n\n<code>{binance_id}</code>\n\nبعد التحويل أرسل لنا:\n1️⃣ رقم معرف المعاملة (Transaction ID)\n2️⃣ صورة إيصال التحويل",
    "lang_changed":      "✅ تم تغيير اللغة",
    "new_order_adm":     "🔔 طلب جديد!\n👤 {user}\n📦 {items}\n💰 {total} USDT\n💳 {method}",
    "approve":           "✅ قبول وتسليم",
    "reject":            "❌ رفض",
    "adm_title":         "👑 لوحة التحكم\n\n👥 {users} مستخدم | 📦 {orders} طلب | 💰 {rev} USDT",
    "adm_add_cat":       "📂 إضافة قسم",
    "adm_add_prod":      "➕ إضافة منتج",
    "adm_manage":        "🗂️ إدارة الأقسام",
    "adm_del":           "🗑️ حذف",
    "adm_orders":        "📋 الطلبات",
    "adm_broadcast":     "📣 رسالة جماعية",
    "adm_tree":          "🌳 هيكل المنتجات",
    "adm_edit_cat":      "✏️ تعديل قسم",
    "adm_edit_prod":     "✏️ تعديل منتج",
    "adm_move_cat":      "📁 نقل قسم",
    "adm_stock":         "📦 المخزن الرقمي",
    "adm_discount":      "🏷️ إدارة الخصومات",
    "sel_parent":        "📂 اختر القسم الرئيسي:",
    "no_parent":         "🌐 بدون قسم رئيسي (جذر)",
    "enter_cat_name_ar": "📝 اسم القسم بالعربية:",
    "enter_cat_name_en": "📝 Category name in English:",
    "enter_cat_name_fr": "📝 Nom en Français:",
    "enter_cat_emoji":   "😀 إيموجي القسم (اكتب - للتخطي):",
    "cat_added":         "✅ تم إضافة القسم!",
    "sel_cat_prod":      "📂 اختر القسم الذي سيحتوي المنتج:",
    "enter_name_ar":     "📝 اسم المنتج بالعربية:",
    "enter_name_en":     "📝 Product name in English:",
    "enter_name_fr":     "📝 Nom du produit en Français:",
    "enter_desc_ar":     "📄 الوصف (اكتب - للتخطي):",
    "enter_price":       "💵 السعر بالـ USDT:",
    "enter_image":       "🖼️ أرسل صورة أو اضغط تخطي:",
    "skip":              "⏭️ تخطي",
    "prod_added":        "✅ تم إضافة المنتج!",
    "sel_del":           "🗑️ اختر ما تريد حذفه:",
    "del_cat":           "📂 حذف قسم",
    "del_prod":          "🛍️ حذف منتج",
    "deleted":           "✅ تم الحذف!",
    "enter_broadcast":   "📣 أدخل الرسالة الجماعية:",
    "broadcast_done":    "✅ أُرسلت لـ {n} مستخدم",
    "sel_edit_cat":      "✏️ اختر القسم للتعديل:",
    "sel_edit_prod":     "✏️ اختر المنتج للتعديل:",
    "field_name_ar":     "📝 الاسم عربي",
    "field_name_en":     "📝 الاسم إنجليزي",
    "field_name_fr":     "📝 الاسم فرنسي",
    "field_emoji":       "😀 الإيموجي",
    "field_price":       "💵 السعر",
    "field_desc":        "📄 الوصف",
    "field_status":      "🔛 تفعيل/تعطيل",
    "enter_new_val":     "✏️ أدخل القيمة الجديدة:",
    "edit_done":         "✅ تم التعديل!",
    "sel_move_dest":     "📂 اختر القسم الوجهة:",
    "move_done":         "✅ تم النقل!",
    "toggle_on":         "✅ مفعّل — اضغط لتعطيل",
    "toggle_off":        "❌ معطّل — اضغط لتفعيل",
    "no_products":       "لا توجد منتجات",
    "confirm_del":       "⚠️ تأكيد الحذف؟",
    "yes_del":           "✅ نعم، احذف",
    "cancel":            "❌ إلغاء",
    # مخزن رقمي
    "sel_prod_stock":    "📦 اختر المنتج لإدارة مخزنه:",
    "stock_panel":       "📦 مخزن: {name}\n🔢 متاح: {count} وحدة",
    "adm_add_keys":      "➕ إضافة وحدات",
    "adm_view_keys":     "👁️ عرض الوحدات",
    "adm_clear_keys":    "🗑️ مسح المخزن",
    "enter_keys":        "📋 أرسل الوحدات — كل وحدة في سطر:\n\nمثال:\nuser1:pass1\nuser2:pass2\nabc-key-xyz",
    "keys_added":        "✅ تمت إضافة {n} وحدة!",
    "stock_cleared":     "✅ تم مسح المخزن!",
    "no_stock":          "❌ المخزن فارغ",
    "delivered_key":     "🎉 طلبك #{id} مكتمل!\n\n📦 {name}\n\n🔑 بياناتك:\n<code>{key}</code>",
    "out_of_stock_warn": "⚠️ المخزن نفد للمنتج: {name}",
    "stock_low_warn":    "⚠️ تنبيه: مخزن [{name}] وصل {count} وحدة فقط!",
    # خصومات
    "disc_panel":        "🏷️ إدارة الخصومات\n\nاضغط منتجاً لتعيين خصمه:",
    "disc_for_prod":     "🏷️ خصم على: {name}\n\nالخصم الحالي: {disc}%\n\nأدخل نسبة الخصم الجديدة (0 = بدون خصم):",
    "disc_set":          "✅ تم تعيين خصم {disc}% على [{name}]",
    "disc_badge":        " 🏷️-{disc}%",
    # قوانين
    "rules":             "📋 القوانين",
    "rules_text":        "📋 قوانين المتجر\n\n✏️ هذا النص قابل للتعديل من قِبَل المالك.\n\n• القانون الأول\n• القانون الثاني\n• القانون الثالث",
    # إيداع عبر طرق متعددة
    "deposit_method":    "💳 اختر طريقة الإيداع:",
    "deposit_heleket":   "₿ إيداع عبر Heleket",
    "deposit_binance":   "🟡 إيداع عبر Binance Pay",
    "binance_deposit_instructions": "🟡 إيداع عبر Binance Pay\n\nPayID الخاص بنا:\n<code>{binance_id}</code>\n\n💰 المبلغ المطلوب: {amount} USDT\n\nبعد التحويل أرسل لنا:\n1️⃣ رقم المعاملة (Transaction ID)\n2️⃣ صورة الإيصال",
},
"en": {
    "choose_lang":       "🌐 Choose your language:",
    "main_menu":         "🏠 Main Menu\nHello {name}!",
    "browse":            "🛍️ Browse Products",
    "cart":              "🛒 Cart ({n})",
    "my_orders":         "📦 My Orders",
    "wallet":            "💰 My Wallet",
    "support":           "💬 Support",
    "settings":          "⚙️ Settings",
    "admin":             "👑 Admin Panel",
    "back":              "◀️ Back",
    "back_main":         "🏠 Menu",
    "back_admin":        "◀️ Admin Panel",
    "add_cart":          "🛒 Add to Cart",
    "buy_now":           "⚡ Buy Now",
    "available":         "✅ Available",
    "unlimited":         "∞ Unlimited",
    "out_of_stock":      "❌ Out of Stock",
    "cart_empty":        "🛒 Your cart is empty",
    "total":             "💰 Total",
    "checkout":          "✅ Checkout",
    "clear_cart":        "🗑️ Clear Cart",
    "pay_title":         "💳 Choose payment method:",
    "pay_wallet":        "💰 From Wallet ({b} USDT)",
    "pay_manual":        "📸 Bank / USDT Transfer",
    "pay_crypto":        "₿ CryptoPay",
    "no_balance":        "❌ Insufficient balance\nBalance: {b} USDT",
    "order_done":        "✅ Order #{id} placed!",
    "send_receipt":      "📸 Send receipt image\n\n💳 USDT (TRC20):\nTYourAddressHere",
    "receipt_recv":      "✅ Receipt received! Will be reviewed soon",
    "order_rejected":    "❌ Order #{id} rejected\nContact support",
    "no_orders":         "📦 No orders yet",
    "order_item":        "#{id} | {total} USDT | {status} | {date}",
    "pending":           "⏳ Pending",
    "completed":         "✅ Completed",
    "cancelled":         "❌ Cancelled",
    "wallet_info":       "💰 Balance: {b} USDT",
    "deposit":           "💳 Deposit",
    "deposit_amount":    "💵 Enter amount in USDT (min {min}):",
    "deposit_link":      "🔗 Payment link ready!\n\n💰 Amount: {amount} USDT\n⏳ Valid for 20 minutes\n\nClick below to pay:",
    "deposit_invalid":   "❌ Enter a valid number (min {min} USDT)",
    "deposit_done":      "✅ {amount} USDT added to your wallet!\nNew balance: {balance} USDT",
    "pay_heleket":       "₿ Heleket (Crypto)",
    "pay_binance":       "🟡 Binance Pay (ID)",
    "binance_instructions": "🟡 Pay via Binance Pay\n\nOur PayID:\n<code>{binance_id}</code>\n\n💰 Amount: {amount} USDT\n📝 Order: #{order_id}\n\nAfter paying, press Confirm Payment and send screenshot.",
    "confirm_payment":   "✅ Confirm Payment",
    "lang_changed":      "✅ Language changed",
    "new_order_adm":     "🔔 New Order!\n👤 {user}\n📦 {items}\n💰 {total} USDT\n💳 {method}",
    "approve":           "✅ Approve & Deliver",
    "reject":            "❌ Reject",
    "adm_title":         "👑 Admin Panel\n\n👥 {users} users | 📦 {orders} orders | 💰 {rev} USDT",
    "adm_add_cat":       "📂 Add Category",
    "adm_add_prod":      "➕ Add Product",
    "adm_manage":        "🗂️ Manage",
    "adm_del":           "🗑️ Delete",
    "adm_orders":        "📋 Orders",
    "adm_broadcast":     "📣 Broadcast",
    "adm_tree":          "🌳 Tree View",
    "adm_edit_cat":      "✏️ Edit Category",
    "adm_edit_prod":     "✏️ Edit Product",
    "adm_move_cat":      "📁 Move Category",
    "adm_stock":         "📦 Digital Stock",
    "adm_discount":      "🏷️ Discounts",
    "sel_parent":        "📂 Select parent category:",
    "no_parent":         "🌐 No parent (root)",
    "enter_cat_name_ar": "📝 Name in Arabic:",
    "enter_cat_name_en": "📝 Name in English:",
    "enter_cat_name_fr": "📝 Nom en Français:",
    "enter_cat_emoji":   "😀 Emoji (- to skip):",
    "cat_added":         "✅ Category added!",
    "sel_cat_prod":      "📂 Select category for product:",
    "enter_name_ar":     "📝 Name in Arabic:",
    "enter_name_en":     "📝 Name in English:",
    "enter_name_fr":     "📝 Nom en Français:",
    "enter_desc_ar":     "📄 Description (- to skip):",
    "enter_price":       "💵 Price in USDT:",
    "enter_image":       "🖼️ Send image or skip:",
    "skip":              "⏭️ Skip",
    "prod_added":        "✅ Product added!",
    "sel_del":           "🗑️ Select what to delete:",
    "del_cat":           "📂 Delete Category",
    "del_prod":          "🛍️ Delete Product",
    "deleted":           "✅ Deleted!",
    "enter_broadcast":   "📣 Enter broadcast message:",
    "broadcast_done":    "✅ Sent to {n} users",
    "sel_edit_cat":      "✏️ Choose category to edit:",
    "sel_edit_prod":     "✏️ Choose product to edit:",
    "field_name_ar":     "📝 Name Arabic",
    "field_name_en":     "📝 Name English",
    "field_name_fr":     "📝 Name French",
    "field_emoji":       "😀 Emoji",
    "field_price":       "💵 Price",
    "field_desc":        "📄 Description",
    "field_status":      "🔛 Enable/Disable",
    "enter_new_val":     "✏️ Enter new value:",
    "edit_done":         "✅ Edited!",
    "sel_move_dest":     "📂 Select destination:",
    "move_done":         "✅ Moved!",
    "toggle_on":         "✅ Active — tap to disable",
    "toggle_off":        "❌ Disabled — tap to enable",
    "no_products":       "No products",
    "confirm_del":       "⚠️ Confirm delete?",
    "yes_del":           "✅ Yes, delete",
    "cancel":            "❌ Cancel",
    "sel_prod_stock":    "📦 Select product to manage stock:",
    "stock_panel":       "📦 Stock: {name}\n🔢 Available: {count} units",
    "adm_add_keys":      "➕ Add Units",
    "adm_view_keys":     "👁️ View Units",
    "adm_clear_keys":    "🗑️ Clear Stock",
    "enter_keys":        "📋 Send units — one per line:\n\nExample:\nuser1:pass1\nuser2:pass2\nabc-key-xyz",
    "keys_added":        "✅ Added {n} units!",
    "stock_cleared":     "✅ Stock cleared!",
    "no_stock":          "❌ Stock is empty",
    "delivered_key":     "🎉 Order #{id} complete!\n\n📦 {name}\n\n🔑 Your key:\n<code>{key}</code>",
    "out_of_stock_warn": "⚠️ Stock empty for: {name}",
    "stock_low_warn":    "⚠️ Low stock alert: [{name}] has {count} unit(s) left!",
    "disc_panel":        "🏷️ Discounts — select product:",
    "disc_for_prod":     "🏷️ Discount for: {name}\n\nCurrent: {disc}%\n\nEnter new percentage (0 = no discount):",
    "disc_set":          "✅ Discount {disc}% set for [{name}]",
    "disc_badge":        " 🏷️-{disc}%",
    "rules":             "📋 Rules",
    "rules_text":        "📋 Store Rules\n\n✏️ This text can be edited by the owner.\n\n• Rule one\n• Rule two\n• Rule three",
    "deposit_method":    "💳 Choose deposit method:",
    "deposit_heleket":   "₿ Deposit via Heleket",
    "deposit_binance":   "🟡 Deposit via Binance Pay",
    "binance_deposit_instructions": "🟡 Deposit via Binance Pay\n\nOur PayID:\n<code>{binance_id}</code>\n\n💰 Amount: {amount} USDT\n\nAfter transfer, send us:\n1️⃣ Transaction ID\n2️⃣ Screenshot",
},
"fr": {
    "choose_lang":       "🌐 Choisissez votre langue:",
    "main_menu":         "🏠 Menu Principal\nBonjour {name}!",
    "browse":            "🛍️ Parcourir",
    "cart":              "🛒 Panier ({n})",
    "my_orders":         "📦 Mes Commandes",
    "wallet":            "💰 Mon Portefeuille",
    "support":           "💬 Support",
    "settings":          "⚙️ Paramètres",
    "admin":             "👑 Admin",
    "back":              "◀️ Retour",
    "back_main":         "🏠 Menu",
    "back_admin":        "◀️ Admin",
    "add_cart":          "🛒 Ajouter",
    "buy_now":           "⚡ Acheter",
    "available":         "✅ Disponible",
    "unlimited":         "∞ Illimité",
    "out_of_stock":      "❌ Rupture de stock",
    "cart_empty":        "🛒 Panier vide",
    "total":             "💰 Total",
    "checkout":          "✅ Commander",
    "clear_cart":        "🗑️ Vider",
    "pay_title":         "💳 Mode de paiement:",
    "pay_wallet":        "💰 Portefeuille ({b} USDT)",
    "pay_manual":        "📸 Virement",
    "pay_crypto":        "₿ CryptoPay",
    "no_balance":        "❌ Solde insuffisant\nSolde: {b} USDT",
    "order_done":        "✅ Commande #{id} créée!",
    "send_receipt":      "📸 Envoyez le reçu\n\n💳 USDT (TRC20):\nTYourAddressHere",
    "receipt_recv":      "✅ Reçu reçu! Bientôt examiné",
    "order_rejected":    "❌ Commande #{id} rejetée\nContactez le support",
    "no_orders":         "📦 Aucune commande",
    "order_item":        "#{id} | {total} USDT | {status} | {date}",
    "pending":           "⏳ En attente",
    "completed":         "✅ Complété",
    "cancelled":         "❌ Annulé",
    "wallet_info":       "💰 Solde: {b} USDT",
    "deposit":           "💳 Dépôt",
    "deposit_amount":    "💵 Entrez le montant en USDT (min {min}):",
    "deposit_link":      "🔗 Lien de paiement prêt!\n\n💰 Montant: {amount} USDT\n⏳ Valide 20 minutes\n\nCliquez ci-dessous:",
    "deposit_invalid":   "❌ Entrez un nombre valide (min {min} USDT)",
    "deposit_done":      "✅ {amount} USDT ajouté à votre portefeuille!\nNouveau solde: {balance} USDT",
    "pay_heleket":       "₿ Heleket (Crypto)",
    "pay_binance":       "🟡 Binance Pay (ID)",
    "binance_instructions": "🟡 Payer via Binance Pay\n\nNotre PayID:\n<code>{binance_id}</code>\n\n💰 Montant: {amount} USDT\n📝 Commande: #{order_id}\n\nAprès paiement, appuyez Confirmer et envoyez capture.",
    "confirm_payment":   "✅ Confirmer le paiement",
    "lang_changed":      "✅ Langue modifiée",
    "new_order_adm":     "🔔 Nouvelle commande!\n👤 {user}\n📦 {items}\n💰 {total} USDT\n💳 {method}",
    "approve":           "✅ Approuver",
    "reject":            "❌ Rejeter",
    "adm_title":         "👑 Admin\n\n👥 {users} | 📦 {orders} | 💰 {rev} USDT",
    "adm_add_cat":       "📂 Ajouter catégorie",
    "adm_add_prod":      "➕ Ajouter produit",
    "adm_manage":        "🗂️ Gérer",
    "adm_del":           "🗑️ Supprimer",
    "adm_orders":        "📋 Commandes",
    "adm_broadcast":     "📣 Diffusion",
    "adm_tree":          "🌳 Structure",
    "adm_edit_cat":      "✏️ Modifier Catégorie",
    "adm_edit_prod":     "✏️ Modifier Produit",
    "adm_move_cat":      "📁 Déplacer",
    "adm_stock":         "📦 Stock Numérique",
    "adm_discount":      "🏷️ Réductions",
    "sel_parent":        "📂 Catégorie parente:",
    "no_parent":         "🌐 Sans parent (racine)",
    "enter_cat_name_ar": "📝 Nom en Arabe:",
    "enter_cat_name_en": "📝 Nom en Anglais:",
    "enter_cat_name_fr": "📝 Nom en Français:",
    "enter_cat_emoji":   "😀 Emoji (- pour ignorer):",
    "cat_added":         "✅ Catégorie ajoutée!",
    "sel_cat_prod":      "📂 Sélectionnez la catégorie:",
    "enter_name_ar":     "📝 Nom en Arabe:",
    "enter_name_en":     "📝 Nom en Anglais:",
    "enter_name_fr":     "📝 Nom en Français:",
    "enter_desc_ar":     "📄 Description (- pour ignorer):",
    "enter_price":       "💵 Prix en USDT:",
    "enter_image":       "🖼️ Envoyez une image ou ignorez:",
    "skip":              "⏭️ Ignorer",
    "prod_added":        "✅ Produit ajouté!",
    "sel_del":           "🗑️ Que supprimer?",
    "del_cat":           "📂 Supprimer catégorie",
    "del_prod":          "🛍️ Supprimer produit",
    "deleted":           "✅ Supprimé!",
    "enter_broadcast":   "📣 Entrez le message:",
    "broadcast_done":    "✅ Envoyé à {n} utilisateurs",
    "sel_edit_cat":      "✏️ Choisir catégorie:",
    "sel_edit_prod":     "✏️ Choisir produit:",
    "field_name_ar":     "📝 Nom Arabe",
    "field_name_en":     "📝 Nom Anglais",
    "field_name_fr":     "📝 Nom Français",
    "field_emoji":       "😀 Emoji",
    "field_price":       "💵 Prix",
    "field_desc":        "📄 Description",
    "field_status":      "🔛 Activer/Désactiver",
    "enter_new_val":     "✏️ Entrez la nouvelle valeur:",
    "edit_done":         "✅ Modifié!",
    "sel_move_dest":     "📂 Sélectionnez la destination:",
    "move_done":         "✅ Déplacé!",
    "toggle_on":         "✅ Actif — désactiver",
    "toggle_off":        "❌ Désactivé — activer",
    "no_products":       "Aucun produit",
    "confirm_del":       "⚠️ Confirmer?",
    "yes_del":           "✅ Oui, supprimer",
    "cancel":            "❌ Annuler",
    "sel_prod_stock":    "📦 Sélectionnez le produit:",
    "stock_panel":       "📦 Stock: {name}\n🔢 Disponible: {count} unités",
    "adm_add_keys":      "➕ Ajouter Unités",
    "adm_view_keys":     "👁️ Voir Unités",
    "adm_clear_keys":    "🗑️ Vider Stock",
    "enter_keys":        "📋 Envoyez les unités — une par ligne:",
    "keys_added":        "✅ {n} unités ajoutées!",
    "stock_cleared":     "✅ Stock vidé!",
    "no_stock":          "❌ Stock vide",
    "delivered_key":     "🎉 Commande #{id}!\n\n📦 {name}\n\n🔑 Votre clé:\n<code>{key}</code>",
    "out_of_stock_warn": "⚠️ Stock épuisé: {name}",
    "stock_low_warn":    "⚠️ Alerte stock: [{name}] reste {count} unité(s)!",
    "disc_panel":        "🏷️ Réductions — sélectionnez un produit:",
    "disc_for_prod":     "🏷️ Réduction pour: {name}\n\nActuelle: {disc}%\n\nEntrez le nouveau pourcentage (0 = aucune):",
    "disc_set":          "✅ Réduction {disc}% appliquée à [{name}]",
    "disc_badge":        " 🏷️-{disc}%",
    "rules":             "📋 Règles",
    "rules_text":        "📋 Règles du magasin\n\n✏️ Ce texte peut être modifié par le propriétaire.\n\n• Règle un\n• Règle deux\n• Règle trois",
    "deposit_method":    "💳 Choisir la méthode de dépôt:",
    "deposit_heleket":   "₿ Dépôt via Heleket",
    "deposit_binance":   "🟡 Dépôt via Binance Pay",
    "binance_deposit_instructions": "🟡 Dépôt via Binance Pay\n\nNotre PayID:\n<code>{binance_id}</code>\n\n💰 Montant: {amount} USDT\n\nAprès le transfert, envoyez-nous:\n1️⃣ ID de transaction\n2️⃣ Capture d'écran",
},
}

def t(lang, k, **kw):
    s = TR.get(lang, TR["ar"]).get(k, TR["ar"].get(k, k))
    return s.format(**kw) if kw else s

# ============================================================
# DATABASE  (PostgreSQL via psycopg2)
# ============================================================
def get_conn():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    return conn

def _row(r):
    """تحويل RealDictRow إلى tuple للتوافق مع بقية الكود"""
    return tuple(r.values()) if r else None

def _rows(rs):
    return [tuple(r.values()) for r in rs]

def init_db():
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id BIGINT PRIMARY KEY, username TEXT, name TEXT,
        lang TEXT DEFAULT 'ar', balance REAL DEFAULT 0,
        state TEXT DEFAULT 'main', state_data TEXT DEFAULT '{}'
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS categories (
        id SERIAL PRIMARY KEY,
        parent_id INTEGER DEFAULT NULL,
        name_ar TEXT NOT NULL, name_en TEXT NOT NULL, name_fr TEXT NOT NULL,
        emoji TEXT DEFAULT '📦', is_active INTEGER DEFAULT 1
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id SERIAL PRIMARY KEY,
        category_id INTEGER NOT NULL,
        name_ar TEXT NOT NULL, name_en TEXT NOT NULL, name_fr TEXT NOT NULL,
        desc_ar TEXT, price REAL NOT NULL, stock INTEGER DEFAULT 0,
        image_id TEXT, content TEXT, is_active INTEGER DEFAULT 1,
        discount INTEGER DEFAULT 0
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS carts (
        user_id BIGINT, product_id INTEGER, qty INTEGER DEFAULT 1,
        PRIMARY KEY(user_id, product_id)
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id SERIAL PRIMARY KEY, user_id BIGINT,
        items TEXT, total REAL, discount REAL DEFAULT 0, method TEXT,
        status TEXT DEFAULT 'pending', receipt_id TEXT,
        created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS product_stock (
        id SERIAL PRIMARY KEY,
        product_id INTEGER NOT NULL,
        unit_value TEXT NOT NULL,
        is_used INTEGER DEFAULT 0,
        used_at TIMESTAMP DEFAULT NULL,
        order_id INTEGER DEFAULT NULL
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )""")
    # قيم افتراضية للقوانين
    cur.execute("INSERT INTO settings (key,value) VALUES ('rules_ar','📋 قوانين المتجر\n\n• القانون الأول\n• القانون الثاني\n• القانون الثالث') ON CONFLICT (key) DO NOTHING")
    cur.execute("INSERT INTO settings (key,value) VALUES ('rules_en','📋 Store Rules\n\n• Rule one\n• Rule two\n• Rule three') ON CONFLICT (key) DO NOTHING")
    cur.execute("INSERT INTO settings (key,value) VALUES ('rules_fr','📋 Règles du magasin\n\n• Règle un\n• Règle deux\n• Règle trois') ON CONFLICT (key) DO NOTHING")
    # بيانات تجريبية
    cur.execute("SELECT COUNT(*) FROM categories")
    if cur.fetchone()[0] == 0:
        for pname, pem in [("9Proxy","🔵"), ("PIA Proxy","🟣"), ("922Proxy","🟡")]:
            cur.execute("INSERT INTO categories (name_ar,name_en,name_fr,emoji) VALUES (%s,%s,%s,%s) RETURNING id",
                        (pname, pname, pname, pem))
            pid = cur.fetchone()[0]
            for nar, nen, nfr, em in [("سكني","Residential","Résidentiel","🏠"),
                                       ("داتاسنتر","Datacenter","Datacenter","🖥️"),
                                       ("ستاتيك","Static IPs","IPs Statiques","📌")]:
                cur.execute("INSERT INTO categories (parent_id,name_ar,name_en,name_fr,emoji) VALUES (%s,%s,%s,%s,%s) RETURNING id",
                            (pid, nar, nen, nfr, em))
                sid = cur.fetchone()[0]
                for row in [(sid, f"1GB {nar}", "1GB Plan", "1GB Plan", 3.99, 0),
                            (sid, f"5GB {nar}", "5GB Plan", "5GB Plan", 9.99, 0)]:
                    cur.execute("INSERT INTO products (category_id,name_ar,name_en,name_fr,price,stock) VALUES (%s,%s,%s,%s,%s,%s)", row)
    conn.commit(); conn.close()

# ── columns: categories = [0:id,1:parent_id,2:name_ar,3:name_en,4:name_fr,5:emoji,6:is_active]
# ── columns: products   = [0:id,1:cat_id,2:name_ar,3:name_en,4:name_fr,5:desc,6:price,7:stock,8:image_id,9:content,10:is_active,11:discount]

def upsert_user(uid, username, name):
    c = get_conn(); cur = c.cursor()
    cur.execute("INSERT INTO users (id,username,name) VALUES (%s,%s,%s) ON CONFLICT (id) DO NOTHING", (uid,username,name))
    c.commit(); c.close()

def get_lang(uid):
    c = get_conn(); cur = c.cursor()
    cur.execute("SELECT lang FROM users WHERE id=%s", (uid,))
    r = cur.fetchone(); c.close()
    return r["lang"] if r else "ar"

def set_lang(uid, lang):
    c = get_conn(); cur = c.cursor()
    cur.execute("UPDATE users SET lang=%s WHERE id=%s", (lang, uid))
    c.commit(); c.close()

def get_state(uid):
    c = get_conn(); cur = c.cursor()
    cur.execute("SELECT state, state_data FROM users WHERE id=%s", (uid,))
    r = cur.fetchone(); c.close()
    if r:
        try: return r["state"], json.loads(r["state_data"] or "{}")
        except: return r["state"], {}
    return "main", {}

def set_state(uid, state, data=None):
    c = get_conn(); cur = c.cursor()
    cur.execute("UPDATE users SET state=%s, state_data=%s WHERE id=%s",
                (state, json.dumps(data or {}, ensure_ascii=False), uid))
    c.commit(); c.close()

def clear_state(uid): set_state(uid, "main", {})

# ── Categories ──
def get_categories(parent_id=None):
    c = get_conn(); cur = c.cursor()
    if parent_id is None:
        cur.execute("SELECT * FROM categories WHERE parent_id IS NULL AND is_active=1 ORDER BY id")
    else:
        cur.execute("SELECT * FROM categories WHERE parent_id=%s AND is_active=1 ORDER BY id", (parent_id,))
    r = _rows(cur.fetchall()); c.close(); return r

def get_all_categories_flat():
    c = get_conn(); cur = c.cursor()
    cur.execute("SELECT * FROM categories WHERE is_active=1 ORDER BY id")
    r = _rows(cur.fetchall()); c.close(); return r

def get_category(cid):
    c = get_conn(); cur = c.cursor()
    cur.execute("SELECT * FROM categories WHERE id=%s", (cid,))
    r = cur.fetchone(); c.close(); return _row(r)

def has_subcats(cid):
    c = get_conn(); cur = c.cursor()
    cur.execute("SELECT COUNT(*) FROM categories WHERE parent_id=%s AND is_active=1", (cid,))
    n = cur.fetchone()[0]; c.close(); return n > 0

def get_products_in(cid):
    c = get_conn(); cur = c.cursor()
    cur.execute("SELECT * FROM products WHERE category_id=%s AND is_active=1", (cid,))
    r = _rows(cur.fetchall()); c.close(); return r

def get_product(pid):
    c = get_conn(); cur = c.cursor()
    cur.execute("SELECT * FROM products WHERE id=%s", (pid,))
    r = cur.fetchone(); c.close(); return _row(r)

def db_add_category(parent_id, name_ar, name_en, name_fr, emoji):
    c = get_conn(); cur = c.cursor()
    cur.execute("INSERT INTO categories (parent_id,name_ar,name_en,name_fr,emoji) VALUES (%s,%s,%s,%s,%s)",
                (parent_id, name_ar, name_en, name_fr, emoji))
    c.commit(); c.close()

def db_add_product(cid, nar, nen, nfr, desc, price, img):
    c = get_conn(); cur = c.cursor()
    cur.execute("INSERT INTO products (category_id,name_ar,name_en,name_fr,desc_ar,price,stock,image_id) VALUES (%s,%s,%s,%s,%s,%s,0,%s)",
                (cid, nar, nen, nfr, desc, price, img))
    c.commit(); c.close()

def db_del_cat(cid):
    c = get_conn(); cur = c.cursor()
    def deactivate(cat_id):
        cur.execute("UPDATE categories SET is_active=0 WHERE id=%s", (cat_id,))
        cur.execute("UPDATE products SET is_active=0 WHERE category_id=%s", (cat_id,))
        cur.execute("SELECT id FROM categories WHERE parent_id=%s", (cat_id,))
        for row in cur.fetchall(): deactivate(row[0])
    deactivate(cid); c.commit(); c.close()

def db_del_prod(pid):
    c = get_conn(); cur = c.cursor()
    cur.execute("UPDATE products SET is_active=0 WHERE id=%s", (pid,))
    c.commit(); c.close()

def db_edit_category(cid, field, value):
    allowed = {"name_ar","name_en","name_fr","emoji","parent_id","is_active"}
    if field not in allowed: return
    c = get_conn(); cur = c.cursor()
    cur.execute(f"UPDATE categories SET {field}=%s WHERE id=%s", (value, cid))
    c.commit(); c.close()

def db_edit_product(pid, field, value):
    allowed = {"name_ar","name_en","name_fr","desc_ar","price","content","category_id","is_active","discount"}
    if field not in allowed: return
    c = get_conn(); cur = c.cursor()
    cur.execute(f"UPDATE products SET {field}=%s WHERE id=%s", (value, pid))
    c.commit(); c.close()

# ── Cart ──
def get_cart(uid):
    c = get_conn(); cur = c.cursor()
    cur.execute("""SELECT ca.product_id,ca.qty,p.name_ar,p.name_en,p.name_fr,p.price,p.stock,p.discount
                   FROM carts ca JOIN products p ON ca.product_id=p.id WHERE ca.user_id=%s""", (uid,))
    r = _rows(cur.fetchall()); c.close(); return r

def cart_count(uid):
    c = get_conn(); cur = c.cursor()
    cur.execute("SELECT COALESCE(SUM(qty),0) FROM carts WHERE user_id=%s", (uid,))
    n = cur.fetchone()[0]; c.close(); return n

def add_to_cart(uid, pid, qty=1):
    c = get_conn(); cur = c.cursor()
    cur.execute("""INSERT INTO carts (user_id,product_id,qty) VALUES (%s,%s,%s)
                   ON CONFLICT (user_id,product_id) DO UPDATE SET qty=carts.qty+%s""",
                (uid, pid, qty, qty))
    c.commit(); c.close()

def update_cart_qty(uid, pid, qty):
    c = get_conn(); cur = c.cursor()
    if qty <= 0:
        cur.execute("DELETE FROM carts WHERE user_id=%s AND product_id=%s", (uid, pid))
    else:
        cur.execute("UPDATE carts SET qty=%s WHERE user_id=%s AND product_id=%s", (qty, uid, pid))
    c.commit(); c.close()

def clear_cart(uid):
    c = get_conn(); cur = c.cursor()
    cur.execute("DELETE FROM carts WHERE user_id=%s", (uid,))
    c.commit(); c.close()

# ── Balance ──
def get_balance(uid):
    c = get_conn(); cur = c.cursor()
    cur.execute("SELECT balance FROM users WHERE id=%s", (uid,))
    r = cur.fetchone(); c.close(); return r["balance"] if r else 0.0

def change_balance(uid, amt):
    c = get_conn(); cur = c.cursor()
    cur.execute("UPDATE users SET balance=balance+%s WHERE id=%s", (amt, uid))
    c.commit(); c.close()

# ── Orders ──
def create_order(uid, items, total, discount, method):
    c = get_conn(); cur = c.cursor()
    cur.execute("INSERT INTO orders (user_id,items,total,discount,method) VALUES (%s,%s,%s,%s,%s) RETURNING id",
                (uid, json.dumps(items, ensure_ascii=False), total, discount, method))
    oid = cur.fetchone()[0]; c.commit(); c.close(); return oid

def set_order_status(oid, status, receipt_id=None):
    c = get_conn(); cur = c.cursor()
    if receipt_id:
        cur.execute("UPDATE orders SET status=%s,receipt_id=%s WHERE id=%s", (status, receipt_id, oid))
    else:
        cur.execute("UPDATE orders SET status=%s WHERE id=%s", (status, oid))
    c.commit(); c.close()

def get_order(oid):
    c = get_conn(); cur = c.cursor()
    cur.execute("SELECT * FROM orders WHERE id=%s", (oid,))
    r = cur.fetchone(); c.close(); return _row(r)

def get_user_orders(uid):
    c = get_conn(); cur = c.cursor()
    cur.execute("SELECT * FROM orders WHERE user_id=%s ORDER BY created DESC LIMIT 15", (uid,))
    r = _rows(cur.fetchall()); c.close(); return r

# ── Digital Stock ──
def stock_add_units(pid, units):
    c = get_conn(); cur = c.cursor()
    for u in units:
        if u.strip():
            cur.execute("INSERT INTO product_stock (product_id,unit_value) VALUES (%s,%s)", (pid, u.strip()))
    cur.execute("SELECT COUNT(*) FROM product_stock WHERE product_id=%s AND is_used=0", (pid,))
    count = cur.fetchone()[0]
    cur.execute("UPDATE products SET stock=%s WHERE id=%s", (count, pid))
    c.commit(); c.close(); return count

def stock_pop_unit(pid, order_id=None):
    c = get_conn(); cur = c.cursor()
    cur.execute("SELECT id,unit_value FROM product_stock WHERE product_id=%s AND is_used=0 ORDER BY id ASC LIMIT 1", (pid,))
    row = cur.fetchone()
    if not row: c.close(); return None
    unit_id, value = row[0], row[1]
    cur.execute("UPDATE product_stock SET is_used=1, used_at=CURRENT_TIMESTAMP, order_id=%s WHERE id=%s", (order_id, unit_id))
    cur.execute("SELECT COUNT(*) FROM product_stock WHERE product_id=%s AND is_used=0", (pid,))
    remaining = cur.fetchone()[0]
    cur.execute("UPDATE products SET stock=%s WHERE id=%s", (remaining, pid))
    c.commit(); c.close(); return value

def stock_pop_units(pid, qty, order_id=None):
    return [u for _ in range(qty) if (u := stock_pop_unit(pid, order_id)) is not None]

def stock_count(pid):
    c = get_conn(); cur = c.cursor()
    cur.execute("SELECT COUNT(*) FROM product_stock WHERE product_id=%s AND is_used=0", (pid,))
    n = cur.fetchone()[0]; c.close(); return n

def stock_get_all_units(pid):
    c = get_conn(); cur = c.cursor()
    cur.execute("SELECT id,unit_value,is_used,used_at FROM product_stock WHERE product_id=%s ORDER BY id", (pid,))
    r = _rows(cur.fetchall()); c.close(); return r

def stock_clear(pid):
    c = get_conn(); cur = c.cursor()
    cur.execute("DELETE FROM product_stock WHERE product_id=%s AND is_used=0", (pid,))
    cur.execute("UPDATE products SET stock=0 WHERE id=%s", (pid,))
    c.commit(); c.close()

def has_digital_stock(pid):
    c = get_conn(); cur = c.cursor()
    cur.execute("SELECT COUNT(*) FROM product_stock WHERE product_id=%s", (pid,))
    n = cur.fetchone()[0]; c.close(); return n > 0

def has_available_digital_stock(pid):
    c = get_conn(); cur = c.cursor()
    cur.execute("SELECT COUNT(*) FROM product_stock WHERE product_id=%s AND is_used=0", (pid,))
    n = cur.fetchone()[0]; c.close(); return n > 0

# ── Stats ──
def get_stats():
    c = get_conn(); cur = c.cursor()
    cur.execute("SELECT COUNT(*) FROM users");  u = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM orders"); o = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(SUM(total),0) FROM orders WHERE status='completed'"); r = cur.fetchone()[0]
    c.close(); return u, o, r

def get_all_user_ids():
    c = get_conn(); cur = c.cursor()
    cur.execute("SELECT id FROM users")
    r = [x[0] for x in cur.fetchall()]; c.close(); return r

def get_rules(lang):
    key = f"rules_{lang}" if lang in ("ar","en","fr") else "rules_ar"
    c = get_conn(); cur = c.cursor()
    cur.execute("SELECT value FROM settings WHERE key=%s", (key,))
    r = cur.fetchone(); c.close()
    return r[0] if r else "📋 لا توجد قوانين بعد"

def set_rules(lang, text):
    key = f"rules_{lang}" if lang in ("ar","en","fr") else "rules_ar"
    c = get_conn(); cur = c.cursor()
    cur.execute("INSERT INTO settings (key,value) VALUES (%s,%s) ON CONFLICT (key) DO UPDATE SET value=%s", (key, text, text))
    c.commit(); c.close()

# ── Stock from digital or product.stock ──
def get_real_stock(p):
    """إرجاع الكمية الفعلية حسب نظام المخزن المستخدم"""
    if has_digital_stock(p[0]):
        return stock_count(p[0])  # stock_count تحسب is_used=0 فقط
    return p[7]

# ============================================================
# HELPERS
# ============================================================
def is_admin(uid): return uid in ADMIN_IDS

def cat_name(cat, lang):
    if lang=="en": return cat[3]
    if lang=="fr": return cat[4]
    return cat[2]

def prod_name(p, lang):
    if lang=="en": return p[3]
    if lang=="fr": return p[4]
    return p[2]

def calc_total(cart):
    """حساب الإجمالي مع خصم كل منتج على حدة"""
    subtotal = 0.0; disc_total = 0.0
    for item in cart:
        pid,qty,nar,nen,nfr,price,stock,discount = item
        item_total = price * qty
        item_disc  = item_total * (discount or 0) / 100
        subtotal   += item_total
        disc_total += item_disc
    final = subtotal - disc_total
    return subtotal, disc_total, final

def get_breadcrumb(cat_id, lang):
    path = []; cid = cat_id; visited = set()
    while cid and cid not in visited:
        visited.add(cid); cat = get_category(cid)
        if not cat: break
        path.insert(0, f"{cat[5]} {cat_name(cat,lang)}")
        cid = cat[1]
    return " › ".join(path)

def _cat_depth(cat_id, _seen=None):
    if _seen is None: _seen = set()
    if cat_id in _seen: return 0
    _seen.add(cat_id); cat = get_category(cat_id)
    if not cat or not cat[1]: return 0
    return 1 + _cat_depth(cat[1], _seen)

def _count_all_products(cat_id):
    total = len(get_products_in(cat_id))
    for sc in get_categories(cat_id): total += _count_all_products(sc[0])
    return total

def _build_tree(lang):
    def build(parent_id, prefix=""):
        cats = get_categories(parent_id); lines = []
        for i, c in enumerate(cats):
            last = i == len(cats) - 1
            conn = "└──" if last else "├──"
            child_px = prefix + ("    " if last else "│   ")
            prods = get_products_in(c[0]); has_sub = has_subcats(c[0])
            pc = f" ({len(prods)})" if prods and not has_sub else ""
            lines.append(f"{prefix}{conn} {c[5]} {cat_name(c,lang)}{pc}")
            if has_sub: lines.extend(build(c[0], child_px))
            else:
                for j, p in enumerate(prods):
                    pl    = "└──" if j==len(prods)-1 else "├──"
                    stock = get_real_stock(p)
                    s_str = "∞" if stock==-1 else ("❌" if stock==0 else str(stock))
                    disc  = f" 🏷️-{p[11]}%" if p[11] else ""
                    lines.append(f"{child_px}{pl} 🔹 {prod_name(p,lang)} — {p[6]}${disc} [{s_str}]")
        return lines
    rows = ["🛍️ هيكل المنتجات\n" + "─"*24] + build(None)
    return "\n".join(rows) if len(rows) > 1 else "لا توجد أقسام بعد"

# ============================================================
# SEND HELPERS
# ============================================================
async def send_or_edit(update, text, kb, parse_mode=None):
    markup = InlineKeyboardMarkup(kb) if kb else None
    q = update.callback_query
    if q:
        try:
            await q.edit_message_text(text, reply_markup=markup, parse_mode=parse_mode); return
        except Exception: pass
        try:
            await q.message.reply_text(text, reply_markup=markup, parse_mode=parse_mode)
        except Exception as e: logging.error(f"send_or_edit: {e}")
    elif update.message:
        await update.message.reply_text(text, reply_markup=markup, parse_mode=parse_mode)

async def send_main_menu(update, ctx, lang=None):
    uid  = update.effective_user.id
    if not lang: lang = get_lang(uid)
    n    = cart_count(uid)
    name = update.effective_user.first_name or "👤"
    clear_state(uid)
    rows = [
        [KeyboardButton(t(lang,"browse")), KeyboardButton(t(lang,"my_orders"))],
        [KeyboardButton(t(lang,"wallet")), KeyboardButton(t(lang,"rules"))],
        [KeyboardButton(t(lang,"support")), KeyboardButton(t(lang,"settings"))],
    ]
    if is_admin(uid): rows.append([KeyboardButton(t(lang,"admin"))])
    rkb  = ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=False)
    q = update.callback_query
    target = q.message if q else update.message
    if target:
        await target.reply_text(t(lang,"main_menu",name=name), reply_markup=rkb)

async def reply_admin(update, ctx, lang):
    u, o, r = get_stats()
    kb = [
        [InlineKeyboardButton(f"📂 {t(lang,'adm_add_cat')}",  callback_data="adm:add_cat"),
         InlineKeyboardButton(f"➕ {t(lang,'adm_add_prod')}", callback_data="adm:add_prod")],
        [InlineKeyboardButton(f"📦 {t(lang,'adm_stock')}",    callback_data="adm:stock"),
         InlineKeyboardButton(f"🏷️ {t(lang,'adm_discount')}",  callback_data="adm:discount")],
        [InlineKeyboardButton(f"🗂️ {t(lang,'adm_manage')}",   callback_data="adm:manage"),
         InlineKeyboardButton(f"🗑️ {t(lang,'adm_del')}",      callback_data="adm:del")],
        [InlineKeyboardButton(f"📋 {t(lang,'adm_orders')}",   callback_data="adm:orders"),
         InlineKeyboardButton(f"📣 {t(lang,'adm_broadcast')}", callback_data="adm:broadcast")],
        [InlineKeyboardButton(f"📋 تعديل القوانين",            callback_data="adm:edit_rules")],
        [InlineKeyboardButton(f"🏠 {t(lang,'back_main')}",    callback_data="go_main")],
    ]
    await send_or_edit(update, t(lang,"adm_title",users=u,orders=o,rev=f"{r:.2f}"), kb)

# ============================================================
# /start
# ============================================================
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    upsert_user(u.id, u.username or "", u.first_name or "")
    clear_state(u.id)
    kb = [[
        InlineKeyboardButton("🇸🇦 العربية", callback_data="lang:ar"),
        InlineKeyboardButton("🇬🇧 English",  callback_data="lang:en"),
        InlineKeyboardButton("🇫🇷 Français", callback_data="lang:fr"),
    ]]
    await update.message.reply_text(
        f"👋 {STORE_NAME}\n\n🌐 اختر لغتك / Choose language:",
        reply_markup=InlineKeyboardMarkup(kb))

# ============================================================
# MESSAGE HANDLER
# ============================================================
async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid   = update.effective_user.id
    lang  = get_lang(uid)
    text  = (update.message.text or "").strip()
    state, sdata = get_state(uid)

    async def reply(msg): await update.message.reply_text(msg)

    # ── Admin input flows ──
    if state == "await_cat_ar":
        sdata["name_ar"] = text; set_state(uid, "await_cat_en", sdata)
        await reply(t(lang,"enter_cat_name_en")); return

    if state == "await_cat_en":
        sdata["name_en"] = text; set_state(uid, "await_cat_fr", sdata)
        await reply(t(lang,"enter_cat_name_fr")); return

    if state == "await_cat_fr":
        sdata["name_fr"] = text; set_state(uid, "await_cat_emoji", sdata)
        await reply(t(lang,"enter_cat_emoji")); return

    if state == "await_cat_emoji":
        emoji = text if text != "-" else "📦"
        db_add_category(sdata.get("parent_id"), sdata["name_ar"], sdata["name_en"], sdata["name_fr"], emoji)
        clear_state(uid)
        await reply(t(lang,"cat_added"))
        await reply_admin(update, ctx, lang); return

    if state == "await_prod_ar":
        sdata["name_ar"] = text; set_state(uid, "await_prod_en", sdata)
        await reply(t(lang,"enter_name_en")); return

    if state == "await_prod_en":
        sdata["name_en"] = text; set_state(uid, "await_prod_fr", sdata)
        await reply(t(lang,"enter_name_fr")); return

    if state == "await_prod_fr":
        sdata["name_fr"] = text; set_state(uid, "await_prod_desc", sdata)
        await reply(t(lang,"enter_desc_ar")); return

    if state == "await_prod_desc":
        sdata["desc"] = "" if text == "-" else text
        set_state(uid, "await_prod_price", sdata)
        await reply(t(lang,"enter_price")); return

    if state == "await_prod_price":
        try:
            sdata["price"] = float(text); set_state(uid, "await_prod_image", sdata)
            kb = [[InlineKeyboardButton(f"⏭️ {t(lang,'skip')}", callback_data="skipimg")]]
            await update.message.reply_text(t(lang,"enter_image"), reply_markup=InlineKeyboardMarkup(kb))
        except: await reply("❌ أدخل رقم مثل: 9.99")
        return

    if state == "await_edit_val" and is_admin(uid):
        field = sdata.get("field"); pid = sdata.get("edit_prod_id"); cid = sdata.get("edit_cat_id")
        val   = text
        try:
            if field == "price": val = float(val)
            elif field == "discount":
                val = int(float(val))
                if not 0 <= val <= 100: raise ValueError
        except:
            await reply("❌ قيمة غير صحيحة"); return
        if pid:   db_edit_product(pid, field, val)
        elif cid: db_edit_category(cid, field, val)
        clear_state(uid)
        await reply(t(lang,"edit_done"))
        await reply_admin(update, ctx, lang); return

    if state == "await_stock_keys" and is_admin(uid):
        pid   = sdata.get("stock_pid")
        lines = [l for l in text.splitlines() if l.strip()]
        if not lines: await reply("❌ أرسل وحدة واحدة على الأقل!"); return
        count = stock_add_units(pid, lines)
        clear_state(uid)
        await reply(t(lang,"keys_added", n=len(lines)))
        p = get_product(pid); name = prod_name(p, lang) if p else str(pid)
        kb = [
            [InlineKeyboardButton(f"➕ {t(lang,'adm_add_keys')}", callback_data=f"stk:add:{pid}"),
             InlineKeyboardButton(f"👁️ {t(lang,'adm_view_keys')}", callback_data=f"stk:view:{pid}")],
            [InlineKeyboardButton(f"🗑️ {t(lang,'adm_clear_keys')}", callback_data=f"stk:clear:{pid}")],
            [InlineKeyboardButton(f"◀️ {t(lang,'back_admin')}", callback_data="adm:stock")],
        ]
        await update.message.reply_text(
            t(lang,"stock_panel",name=name,count=count),
            reply_markup=InlineKeyboardMarkup(kb)); return

    if state == "await_disc_val" and is_admin(uid):
        pid = sdata.get("disc_pid")
        try:
            disc = int(float(text))
            if not 0 <= disc <= 100: raise ValueError
            db_edit_product(pid, "discount", disc)
            p = get_product(pid); name = prod_name(p, lang) if p else str(pid)
            clear_state(uid)
            await reply(t(lang,"disc_set", disc=disc, name=name))
            await reply_admin(update, ctx, lang)
        except: await reply("❌ أدخل رقماً بين 0 و 100")
        return

    if state == "await_broadcast" and is_admin(uid):
        users = get_all_user_ids(); sent = 0
        for u2 in users:
            try: await ctx.bot.send_message(u2, f"📣 {STORE_NAME}\n\n{text}"); sent += 1
            except: pass
        clear_state(uid)
        await reply(t(lang,"broadcast_done",n=sent))
        await reply_admin(update, ctx, lang); return

    if state == "await_rules_text" and is_admin(uid):
        rl = sdata.get("rules_lang", "ar")
        set_rules(rl, text)
        clear_state(uid)
        flag = {"ar":"🇸🇦","en":"🇬🇧","fr":"🇫🇷"}.get(rl,"")
        await reply(f"✅ تم تحديث القوانين {flag}")
        await reply_admin(update, ctx, lang); return

    if state == "await_receipt":
        await reply("📸 الرجاء إرسال صورة الإيصال فقط"); return

    if state == "await_binance_receipt":
        oid = sdata.get("order_id")
        # المستخدم يرسل Transaction ID نصاً
        set_state(uid, "await_binance_screenshot", {"order_id": oid, "txid": text})
        await reply("📸 الآن أرسل صورة إيصال التحويل:")
        return

    if state == "await_binance_deposit_receipt":
        # المستخدم يرسل Transaction ID نصاً للإيداع
        amount = sdata.get("amount", 0)
        set_state(uid, "await_binance_deposit_receipt", {"amount": amount, "txid": text})
        await reply("📸 الآن أرسل صورة إيصال التحويل:")
        return

    if state == "await_deposit_amount":
        try:
            amount = float(text.replace(",", "."))
            if amount < MIN_DEPOSIT:
                await reply(t(lang, "deposit_invalid", min=MIN_DEPOSIT)); return
            clear_state(uid)
            pay_url = await _create_heleket_deposit(amount, uid)
            if pay_url:
                kb = [
                    [InlineKeyboardButton("💳 ادفع الآن", url=pay_url)],
                    [InlineKeyboardButton(f"🏠 {t(lang,'back_main')}", callback_data="go_main")],
                ]
                await update.message.reply_text(
                    t(lang, "deposit_link", amount=f"{amount:.2f}"),
                    reply_markup=InlineKeyboardMarkup(kb))
            else:
                await reply("❌ تعذر إنشاء رابط الدفع، تواصل مع الدعم.")
        except ValueError:
            await reply(t(lang, "deposit_invalid", min=MIN_DEPOSIT))
        return

    if state == "await_deposit_amount_binance":
        try:
            amount = float(text.replace(",", "."))
            if amount < MIN_DEPOSIT:
                await reply(t(lang, "deposit_invalid", min=MIN_DEPOSIT)); return
            set_state(uid, "await_binance_deposit_receipt", {"amount": amount})
            kb = [[InlineKeyboardButton(f"🏠 {t(lang,'back_main')}", callback_data="go_main")]]
            await update.message.reply_text(
                t(lang, "binance_deposit_instructions",
                  binance_id=BINANCE_PAY_ID, amount=f"{amount:.2f}"),
                reply_markup=InlineKeyboardMarkup(kb),
                parse_mode="HTML")
        except ValueError:
            await reply(t(lang, "deposit_invalid", min=MIN_DEPOSIT))
        return

    # ── Reply Keyboard ──
    browse_key   = t(lang,"browse")
    cart_base    = t(lang,"cart",n=0).split("(")[0].strip()
    orders_key   = t(lang,"my_orders")
    wallet_key   = t(lang,"wallet")
    support_key  = t(lang,"support")
    settings_key = t(lang,"settings")
    admin_key    = t(lang,"admin")

    if text == browse_key:          await _show_browse_root(update, ctx, lang)
    elif text.startswith(cart_base): await _show_cart(update, ctx, lang)
    elif text == orders_key:         await _show_orders(update, ctx, lang)
    elif text == wallet_key:         await _show_wallet(update, ctx, lang)
    elif text == t(lang,"rules"):
        kb = [[InlineKeyboardButton(f"🏠 {t(lang,'back_main')}", callback_data="go_main")]]
        await update.message.reply_text(get_rules(lang), reply_markup=InlineKeyboardMarkup(kb))
    elif text == support_key:
        kb = [[InlineKeyboardButton(f"🏠 {t(lang,'back_main')}", callback_data="go_main")]]
        await update.message.reply_text(f"💬 {SUPPORT_USERNAME}", reply_markup=InlineKeyboardMarkup(kb))
    elif text == settings_key:       await _show_settings(update, ctx, lang)
    elif text == admin_key and is_admin(uid): await reply_admin(update, ctx, lang)
    else:                            await send_main_menu(update, ctx, lang)

async def handle_photo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id; lang = get_lang(uid)
    state, sdata = get_state(uid)

    if state == "await_prod_image":
        img = update.message.photo[-1].file_id
        db_add_product(sdata.get("cat_id"), sdata.get("name_ar",""), sdata.get("name_en",""),
                       sdata.get("name_fr",""), sdata.get("desc",""), sdata.get("price",0), img)
        clear_state(uid)
        await update.message.reply_text(t(lang,"prod_added"))
        await reply_admin(update, ctx, lang); return

    if state == "await_receipt":
        oid = sdata.get("order_id")
        if not oid: return
        fid = update.message.photo[-1].file_id
        set_order_status(oid, "pending", fid)
        clear_state(uid)
        for adm in ADMIN_IDS:
            try:
                kb = [[InlineKeyboardButton(t("ar","approve"), callback_data=f"approve:{oid}"),
                       InlineKeyboardButton(t("ar","reject"),  callback_data=f"reject:{oid}")]]
                await ctx.bot.send_photo(adm, photo=fid,
                    caption=f"📸 إيصال\nطلب #{oid} | مستخدم {uid}",
                    reply_markup=InlineKeyboardMarkup(kb))
            except Exception as e: logging.error(e)
        kb = [[InlineKeyboardButton(f"🏠 {t(lang,'back_main')}", callback_data="go_main")]]
        await update.message.reply_text(t(lang,"receipt_recv"), reply_markup=InlineKeyboardMarkup(kb))

    if state == "await_binance_screenshot":
        oid  = sdata.get("order_id")
        txid = sdata.get("txid", "—")
        if not oid: return
        fid  = update.message.photo[-1].file_id
        set_order_status(oid, "pending", fid)
        clear_state(uid)
        for adm in ADMIN_IDS:
            try:
                kb = [[InlineKeyboardButton(t("ar","approve"), callback_data=f"approve:{oid}"),
                       InlineKeyboardButton(t("ar","reject"),  callback_data=f"reject:{oid}")]]
                await ctx.bot.send_photo(adm, photo=fid,
                    caption=f"🟡 Binance Pay\nطلب #{oid} | مستخدم {uid}\nTransaction ID: {txid}",
                    reply_markup=InlineKeyboardMarkup(kb))
            except Exception as e: logging.error(e)
        kb = [[InlineKeyboardButton(f"🏠 {t(lang,'back_main')}", callback_data="go_main")]]
        await update.message.reply_text(t(lang,"receipt_recv"), reply_markup=InlineKeyboardMarkup(kb))

    if state == "await_binance_deposit_receipt":
        amount = sdata.get("amount", 0)
        txid   = sdata.get("txid", "—")
        fid    = update.message.photo[-1].file_id
        clear_state(uid)
        for adm in ADMIN_IDS:
            try:
                kb_adm = [[
                    InlineKeyboardButton(f"✅ قبول الإيداع", callback_data=f"dep_approve:{uid}:{amount}"),
                    InlineKeyboardButton(f"❌ رفض",          callback_data=f"dep_reject:{uid}:{amount}"),
                ]]
                await ctx.bot.send_photo(adm, photo=fid,
                    caption=f"🟡 Binance Pay — طلب إيداع\n👤 مستخدم: {uid}\n💰 المبلغ: {amount} USDT\n🔖 Transaction ID: {txid}",
                    reply_markup=InlineKeyboardMarkup(kb_adm))
            except Exception as e: logging.error(e)
        kb = [[InlineKeyboardButton(f"🏠 {t(lang,'back_main')}", callback_data="go_main")]]
        await update.message.reply_text(t(lang,"receipt_recv"), reply_markup=InlineKeyboardMarkup(kb))

# ============================================================
# CALLBACK HANDLER — كل الأزرار
# ============================================================
async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q    = update.callback_query
    uid  = q.from_user.id; lang = get_lang(uid); d = q.data

    # للأزرار العادية نجيب فوراً، لكن approve/reject ستجيب بنفسها
    if not d.startswith("approve:") and not d.startswith("reject:"):
        try:
            await q.answer()
        except Exception:
            pass

    # اللغة
    if d.startswith("lang:"):
        lang = d.split(":")[1]; set_lang(uid, lang); clear_state(uid)
        try: await q.message.delete()
        except: pass
        await send_main_menu(update, ctx, lang); return

    if d == "go_main":
        clear_state(uid); await send_main_menu(update, ctx, lang); return

    # تصفح
    if d.startswith("browse:"):
        await _cb_browse(update, ctx, lang, d.split(":",1)[1]); return

    if d.startswith("prod:"):
        await _cb_product(update, ctx, lang, int(d.split(":")[1])); return

    if d.startswith("buynow:"):
        pid = int(d.split(":")[1]); clear_cart(uid); add_to_cart(uid, pid)
        await _show_payment(update, ctx, lang); return

    # سلة
    if d == "go_cart": await _show_cart(update, ctx, lang); return

    if d.startswith("cq:"):
        _, act, pid = d.split(":"); pid = int(pid)
        cart = get_cart(uid); cur_qty = next((i[1] for i in cart if i[0]==pid), 0)
        if act=="inc":   update_cart_qty(uid, pid, cur_qty+1)
        elif act=="dec": update_cart_qty(uid, pid, cur_qty-1)
        elif act=="del": update_cart_qty(uid, pid, 0)
        await _show_cart(update, ctx, lang); return

    if d == "do_clear":
        clear_cart(uid); await _show_cart(update, ctx, lang); return

    if d == "do_checkout":
        await _show_payment(update, ctx, lang); return

    # دفع
    if d.startswith("pay:"):
        await _cb_payment(update, ctx, lang, d.split(":")[1]); return

    # طلبات / محفظة / إعدادات
    if d == "go_orders":   await _show_orders(update, ctx, lang); return
    if d == "go_wallet":   await _show_wallet(update, ctx, lang); return
    if d == "go_settings": await _show_settings(update, ctx, lang); return
    if d == "go_support":
        kb = [[InlineKeyboardButton(f"🏠 {t(lang,'back_main')}", callback_data="go_main")]]
        await send_or_edit(update, f"💬 {SUPPORT_USERNAME}", kb); return

    if d.startswith("setlang:"):
        nl = d.split(":")[1]; set_lang(uid, nl)
        try: await q.message.delete()
        except: pass
        await send_main_menu(update, ctx, nl); return

    # أدمن
    if d == "go_admin" and is_admin(uid):
        clear_state(uid); await reply_admin(update, ctx, lang); return

    if d.startswith("adm:") and is_admin(uid):
        await _cb_admin(update, ctx, lang, d.split(":",1)[1]); return

    # حذف — تأكيد
    if d.startswith("delcat:") and is_admin(uid):
        cid = int(d.split(":")[1]); cat = get_category(cid)
        name = cat_name(cat, lang) if cat else "?"
        kb = [[InlineKeyboardButton(f"✅ {t(lang,'yes_del')}", callback_data=f"dodelcat:{cid}"),
               InlineKeyboardButton(f"❌ {t(lang,'cancel')}",  callback_data="adm:del")]]
        await send_or_edit(update, f"⚠️ حذف: {cat[5] if cat else ''} {name}؟", kb); return

    if d.startswith("delprod:") and is_admin(uid):
        pid = int(d.split(":")[1]); p = get_product(pid)
        name = prod_name(p, lang) if p else "?"
        kb = [[InlineKeyboardButton(f"✅ {t(lang,'yes_del')}", callback_data=f"dodelprod:{pid}"),
               InlineKeyboardButton(f"❌ {t(lang,'cancel')}",  callback_data="adm:del")]]
        await send_or_edit(update, f"⚠️ حذف: {name}؟", kb); return

    if d.startswith("dodelcat:") and is_admin(uid):
        db_del_cat(int(d.split(":")[1])); await q.answer(t(lang,"deleted"), show_alert=True)
        clear_state(uid); await reply_admin(update, ctx, lang); return

    if d.startswith("dodelprod:") and is_admin(uid):
        db_del_prod(int(d.split(":")[1])); await q.answer(t(lang,"deleted"), show_alert=True)
        clear_state(uid); await reply_admin(update, ctx, lang); return

    # إضافة قسم / منتج
    if d.startswith("catpar:") and is_admin(uid):
        val = d.split(":")[1]; parent_id = None if val=="none" else int(val)
        set_state(uid, "await_cat_ar", {"parent_id": parent_id})
        kb = [[InlineKeyboardButton(f"◀️ {t(lang,'back_admin')}", callback_data="go_admin")]]
        await send_or_edit(update, t(lang,"enter_cat_name_ar"), kb); return

    if d.startswith("prodcat:") and is_admin(uid):
        cid = int(d.split(":")[1]); set_state(uid, "await_prod_ar", {"cat_id": cid})
        kb = [[InlineKeyboardButton(f"◀️ {t(lang,'back_admin')}", callback_data="go_admin")]]
        await send_or_edit(update, t(lang,"enter_name_ar"), kb); return

    if d == "skipimg" and is_admin(uid):
        _, sdata = get_state(uid)
        db_add_product(sdata.get("cat_id"), sdata.get("name_ar",""), sdata.get("name_en",""),
                       sdata.get("name_fr",""), sdata.get("desc",""), sdata.get("price",0), None)
        clear_state(uid); await send_or_edit(update, t(lang,"prod_added"), [])
        await reply_admin(update, ctx, lang); return

    # تعديل قسم — FIX: cat[5]=emoji, cat[6]=is_active
    if d.startswith("editcat:") and is_admin(uid):
        cid = int(d.split(":")[1])
        _, sdata = get_state(uid); sdata["edit_cat_id"] = cid
        set_state(uid, "edit_cat", sdata)
        cat = get_category(cid)
        if not cat: await q.answer("❌", show_alert=True); return
        name  = cat_name(cat, lang)
        s_lbl = t(lang,"toggle_on") if cat[6] else t(lang,"toggle_off")
        kb = [
            [InlineKeyboardButton(f"📝 {t(lang,'field_name_ar')}", callback_data="ecf:name_ar"),
             InlineKeyboardButton(f"📝 {t(lang,'field_name_en')}", callback_data="ecf:name_en")],
            [InlineKeyboardButton(f"📝 {t(lang,'field_name_fr')}", callback_data="ecf:name_fr"),
             InlineKeyboardButton(f"😀 {t(lang,'field_emoji')}",   callback_data="ecf:emoji")],
            [InlineKeyboardButton(f"🔛 {s_lbl}", callback_data="ecf:toggle")],
            [InlineKeyboardButton(f"◀️ {t(lang,'back')}", callback_data="adm:edit_cat")],
        ]
        await send_or_edit(update, f"✏️ {cat[5]} {name}", kb); return

    if d.startswith("ecf:") and is_admin(uid):
        field = d.split(":")[1]; _, sdata = get_state(uid); cid = sdata.get("edit_cat_id")
        if not cid: await reply_admin(update, ctx, lang); return
        if field == "toggle":
            cat = get_category(cid)
            db_edit_category(cid, "is_active", 0 if cat[6] else 1)
            await q.answer(t(lang,"edit_done"), show_alert=True)
            clear_state(uid); await reply_admin(update, ctx, lang); return
        sdata["field"] = field; set_state(uid, "await_edit_val", sdata)
        kb = [[InlineKeyboardButton(f"◀️ {t(lang,'back')}", callback_data=f"editcat:{cid}")]]
        await send_or_edit(update, t(lang,"enter_new_val"), kb); return

    # تعديل منتج — FIX: p[10]=is_active, p[11]=discount
    if d.startswith("editprod:") and is_admin(uid):
        pid = int(d.split(":")[1])
        _, sdata = get_state(uid); sdata["edit_prod_id"] = pid
        set_state(uid, "edit_prod", sdata)
        p = get_product(pid)
        if not p: await q.answer("❌", show_alert=True); return
        name  = prod_name(p, lang)
        s_lbl = t(lang,"toggle_on") if p[10] else t(lang,"toggle_off")
        stock = get_real_stock(p)
        disc  = p[11] or 0
        kb = [
            [InlineKeyboardButton(f"📝 {t(lang,'field_name_ar')}", callback_data="epf:name_ar"),
             InlineKeyboardButton(f"📝 {t(lang,'field_name_en')}", callback_data="epf:name_en")],
            [InlineKeyboardButton(f"📝 {t(lang,'field_name_fr')}", callback_data="epf:name_fr"),
             InlineKeyboardButton(f"📄 {t(lang,'field_desc')}",    callback_data="epf:desc_ar")],
            [InlineKeyboardButton(f"💵 {t(lang,'field_price')}",   callback_data="epf:price"),
             InlineKeyboardButton(f"🏷️ {t(lang,'adm_discount')} ({disc}%)", callback_data="epf:discount")],
            [InlineKeyboardButton(f"🔛 {s_lbl}", callback_data="epf:toggle")],
            [InlineKeyboardButton(f"◀️ {t(lang,'back')}", callback_data="adm:edit_prod")],
        ]
        s_str = "∞" if stock==-1 else str(stock)
        await send_or_edit(update, f"✏️ {name}\n💵 {p[6]}$ | 📦 {s_str} | 🏷️ {disc}%", kb); return

    if d.startswith("epf:") and is_admin(uid):
        field = d.split(":")[1]; _, sdata = get_state(uid); pid = sdata.get("edit_prod_id")
        if not pid: await reply_admin(update, ctx, lang); return
        if field == "toggle":
            p = get_product(pid)
            db_edit_product(pid, "is_active", 0 if p[10] else 1)
            await q.answer(t(lang,"edit_done"), show_alert=True)
            clear_state(uid); await reply_admin(update, ctx, lang); return
        sdata["field"] = field; set_state(uid, "await_edit_val", sdata)
        kb = [[InlineKeyboardButton(f"◀️ {t(lang,'back')}", callback_data=f"editprod:{pid}")]]
        await send_or_edit(update, t(lang,"enter_new_val"), kb); return

    # نقل قسم
    if d.startswith("movecat:") and is_admin(uid):
        cid = int(d.split(":")[1]); _, sdata = get_state(uid); sdata["move_cat_id"] = cid
        set_state(uid, "move_cat", sdata); cat = get_category(cid)
        all_cats = get_all_categories_flat()
        kb = [[InlineKeyboardButton(f"🌐 {t(lang,'no_parent')}", callback_data="movedest:none")]]
        for c in all_cats:
            if c[0]==cid: continue
            dep = "  " * _cat_depth(c[0])
            kb.append([InlineKeyboardButton(f"{dep}{c[5]} {cat_name(c,lang)}", callback_data=f"movedest:{c[0]}")])
        kb.append([InlineKeyboardButton(f"◀️ {t(lang,'back')}", callback_data="adm:move_cat")])
        await send_or_edit(update, f"{t(lang,'sel_move_dest')}\n📂 {cat[5]} {cat_name(cat,lang)}", kb); return

    if d.startswith("movedest:") and is_admin(uid):
        dest_raw = d.split(":")[1]; _, sdata = get_state(uid); cid = sdata.get("move_cat_id")
        if cid:
            db_edit_category(cid, "parent_id", None if dest_raw=="none" else int(dest_raw))
            await q.answer(t(lang,"move_done"), show_alert=True)
        clear_state(uid); await reply_admin(update, ctx, lang); return

    # موافقة / رفض طلب
    if d.startswith("approve:") and is_admin(uid):
        try: await q.answer()
        except Exception: pass
        oid = int(d.split(":")[1])
        order = get_order(oid)
        if not order:
            await q.answer("❌ الطلب غير موجود", show_alert=True); return
        if order[6] == "completed":
            await q.answer("✅ الطلب مكتمل بالفعل", show_alert=True); return
        # 1) تحديث حالة الطلب
        set_order_status(oid, "completed")
        # 2) إزالة الأزرار من رسالة الأدمن فوراً
        try:
            await q.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass
        # 3) تأكيد مرئي للأدمن برسالة جديدة
        try:
            await q.message.reply_text(f"✅ تم قبول وتسليم طلب #{oid}")
        except Exception as e:
            logging.error(f"approve admin confirm: {e}")
        # 4) تجهيز المنتجات وتسليمها للمستخدم
        u_lang = get_lang(order[1])
        items  = json.loads(order[2])
        try:
            await _deliver(ctx, order[1], oid, items, u_lang)
        except Exception as e:
            logging.error(f"approve _deliver error: {e}")
            try:
                await ctx.bot.send_message(uid, f"⚠️ خطأ أثناء التسليم للطلب #{oid}:\n{e}")
            except Exception:
                pass
        # 5) إشعار المستخدم بالموافقة
        try:
            kb_user = [[InlineKeyboardButton(f"📦 {t(u_lang,'my_orders')}", callback_data="go_orders")]]
            await ctx.bot.send_message(
                order[1],
                f"✅ طلبك #{oid} تمت الموافقة عليه وجارٍ التسليم.",
                reply_markup=InlineKeyboardMarkup(kb_user))
        except Exception as e:
            logging.error(f"approve notify user: {e}")
        return

    if d.startswith("reject:") and is_admin(uid):
        try: await q.answer()
        except Exception: pass
        oid = int(d.split(":")[1])
        order = get_order(oid)
        if not order:
            await q.answer("❌ الطلب غير موجود", show_alert=True); return
        if order[6] == "cancelled":
            await q.answer("❌ الطلب ملغي بالفعل", show_alert=True); return
        if order[6] == "completed":
            await q.answer("⚠️ لا يمكن رفض طلب مكتمل", show_alert=True); return
        # 1) تحديث الحالة
        set_order_status(oid, "cancelled")
        # 2) إزالة الأزرار من رسالة الأدمن فوراً
        try:
            await q.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass
        # 3) تأكيد مرئي للأدمن
        try:
            await q.message.reply_text(f"❌ تم رفض طلب #{oid}")
        except Exception as e:
            logging.error(f"reject admin confirm: {e}")
        # 4) إشعار المستخدم
        u_lang = get_lang(order[1])
        try:
            await ctx.bot.send_message(order[1], t(u_lang, "order_rejected", id=oid))
        except Exception as e:
            logging.error(f"reject notify user: {e}")
        return

    # مخزن رقمي
    if d.startswith("stk:") and is_admin(uid):
        parts  = d.split(":"); action = parts[1]
        if action == "sel":
            pid = int(parts[2]); p = get_product(pid)
            if not p: await q.answer("❌", show_alert=True); return
            name = prod_name(p, lang); count = stock_count(pid)
            kb = [
                [InlineKeyboardButton(f"➕ {t(lang,'adm_add_keys')}", callback_data=f"stk:add:{pid}"),
                 InlineKeyboardButton(f"👁️ {t(lang,'adm_view_keys')}", callback_data=f"stk:view:{pid}")],
                [InlineKeyboardButton(f"🗑️ {t(lang,'adm_clear_keys')}", callback_data=f"stk:clear:{pid}")],
                [InlineKeyboardButton(f"◀️ {t(lang,'back_admin')}", callback_data="adm:stock")],
            ]
            await send_or_edit(update, t(lang,"stock_panel",name=name,count=count), kb)
        elif action == "add":
            pid = int(parts[2]); set_state(uid, "await_stock_keys", {"stock_pid": pid})
            kb  = [[InlineKeyboardButton(f"◀️ {t(lang,'back')}", callback_data=f"stk:sel:{pid}")]]
            await send_or_edit(update, t(lang,"enter_keys"), kb)
        elif action == "view":
            pid = int(parts[2]); p = get_product(pid); units = stock_get_all_units(pid)
            avail = [u for u in units if not u[2]]; used = [u for u in units if u[2]]
            if not units: await q.answer(t(lang,"no_stock"), show_alert=True); return
            lines = []
            if avail:
                lines.append(f"✅ متاح ({len(avail)}):")
                for i,u in enumerate(avail[:20],1): lines.append(f"  {i}. <code>{u[1]}</code>")
                if len(avail)>20: lines.append(f"  ... و{len(avail)-20} أخرى")
            if used: lines.append(f"\n🔴 مستخدم ({len(used)} وحدة)")
            name = prod_name(p,lang) if p else str(pid)
            txt  = f"📦 {name}\n\n" + "\n".join(lines)
            if len(txt)>4000: txt = txt[:4000]+"..."
            kb = [[InlineKeyboardButton(f"➕ {t(lang,'adm_add_keys')}", callback_data=f"stk:add:{pid}")],
                  [InlineKeyboardButton(f"◀️ {t(lang,'back')}", callback_data=f"stk:sel:{pid}")]]
            await send_or_edit(update, txt, kb)
        elif action == "clear":
            pid = int(parts[2]); p = get_product(pid); name = prod_name(p,lang) if p else str(pid)
            kb  = [[InlineKeyboardButton(f"✅ {t(lang,'yes_del')}", callback_data=f"stk:doclear:{pid}"),
                    InlineKeyboardButton(f"❌ {t(lang,'cancel')}",   callback_data=f"stk:sel:{pid}")]]
            await send_or_edit(update, f"⚠️ مسح وحدات [{name}]؟", kb)
        elif action == "doclear":
            pid = int(parts[2]); stock_clear(pid)
            await q.answer(t(lang,"stock_cleared"), show_alert=True)
            p = get_product(pid); name = prod_name(p,lang) if p else str(pid)
            kb = [[InlineKeyboardButton(f"➕ {t(lang,'adm_add_keys')}", callback_data=f"stk:add:{pid}")],
                  [InlineKeyboardButton(f"◀️ {t(lang,'back_admin')}", callback_data="adm:stock")]]
            await send_or_edit(update, t(lang,"stock_panel",name=name,count=0), kb)
        return

    # خصومات
    if d.startswith("disc:") and is_admin(uid):
        parts = d.split(":"); action = parts[1]
        if action == "sel":
            pid = int(parts[2]); p = get_product(pid)
            if not p: await q.answer("❌", show_alert=True); return
            name = prod_name(p, lang); disc = p[11] or 0
            set_state(uid, "await_disc_val", {"disc_pid": pid})
            kb = [[InlineKeyboardButton(f"◀️ {t(lang,'back_admin')}", callback_data="adm:discount")]]
            await send_or_edit(update, t(lang,"disc_for_prod",name=name,disc=disc), kb)
        return

    # إيداع رصيد — اختيار الطريقة
    if d == "do_deposit":
        kb = [
            [InlineKeyboardButton(f"₿ {t(lang,'deposit_heleket')}", callback_data="deposit:heleket")],
            [InlineKeyboardButton(f"🟡 {t(lang,'deposit_binance')}", callback_data="deposit:binance")],
            [InlineKeyboardButton(f"◀️ {t(lang,'back')}", callback_data="go_wallet")],
        ]
        await send_or_edit(update, t(lang,"deposit_method"), kb); return

    # إيداع عبر Heleket
    if d == "deposit:heleket":
        set_state(uid, "await_deposit_amount", {"method": "heleket"})
        kb = [[InlineKeyboardButton(f"◀️ {t(lang,'back')}", callback_data="go_wallet")]]
        await send_or_edit(update, t(lang,"deposit_amount", min=MIN_DEPOSIT), kb); return

    # إيداع عبر Binance Pay
    if d == "deposit:binance":
        set_state(uid, "await_deposit_amount_binance", {})
        kb = [[InlineKeyboardButton(f"◀️ {t(lang,'back')}", callback_data="go_wallet")]]
        await send_or_edit(update, t(lang,"deposit_amount", min=MIN_DEPOSIT), kb); return

    # تأكيد دفع Binance
    if d.startswith("confirm_binance:"):
        oid = int(d.split(":")[1])
        set_state(uid, "await_receipt", {"order_id": oid})
        kb = [[InlineKeyboardButton(f"🏠 {t(lang,'back_main')}", callback_data="go_main")]]
        await send_or_edit(update, "📸 أرسل صورة إيصال الدفع من Binance Pay:", kb); return

    if d == "noop": return

    # تعديل القوانين — اختيار اللغة
    if d.startswith("editrules:") and is_admin(uid):
        rl = d.split(":")[1]
        set_state(uid, "await_rules_text", {"rules_lang": rl})
        current = get_rules(rl)
        kb = [[InlineKeyboardButton(f"◀️ {t(lang,'back_admin')}", callback_data="adm:edit_rules")]]
        flag = {"ar":"🇸🇦","en":"🇬🇧","fr":"🇫🇷"}.get(rl,"")
        await send_or_edit(update,
            f"📋 {flag} أرسل النص الجديد للقوانين:\n\n(النص الحالي):\n{current}", kb)
        return

    # قبول / رفض إيداع Binance
    if d.startswith("dep_approve:") and is_admin(uid):
        try: await q.answer()
        except: pass
        parts   = d.split(":")
        tgt_uid = int(parts[1]); amount = float(parts[2])
        change_balance(tgt_uid, amount)
        new_bal = get_balance(tgt_uid)
        try: await q.edit_message_reply_markup(reply_markup=None)
        except: pass
        try: await q.message.reply_text(f"✅ تم إضافة {amount} USDT لرصيد المستخدم {tgt_uid}\nرصيده الآن: {new_bal:.2f} USDT")
        except: pass
        u_lang = get_lang(tgt_uid)
        try:
            await ctx.bot.send_message(tgt_uid,
                t(u_lang, "deposit_done", amount=f"{amount:.2f}", balance=f"{new_bal:.2f}"))
        except Exception as e: logging.error(e)
        return

    if d.startswith("dep_reject:") and is_admin(uid):
        try: await q.answer()
        except: pass
        parts   = d.split(":")
        tgt_uid = int(parts[1]); amount = float(parts[2])
        try: await q.edit_message_reply_markup(reply_markup=None)
        except: pass
        try: await q.message.reply_text(f"❌ تم رفض طلب إيداع {amount} USDT للمستخدم {tgt_uid}")
        except: pass
        u_lang = get_lang(tgt_uid)
        try:
            await ctx.bot.send_message(tgt_uid,
                f"❌ تم رفض طلب الإيداع ({amount} USDT)\nتواصل مع الدعم: {SUPPORT_USERNAME}")
        except Exception as e: logging.error(e)
        return

# ============================================================
# PAGE FUNCTIONS
# ============================================================
async def _show_browse_root(update, ctx, lang):
    subcats = get_categories(None); kb = []
    for sc in subcats:
        total = _count_all_products(sc[0])
        kb.append([InlineKeyboardButton(f"{sc[5]}  {cat_name(sc,lang)}  ({total})", callback_data=f"browse:{sc[0]}")])
    kb.append([InlineKeyboardButton(f"🏠 {t(lang,'back_main')}", callback_data="go_main")])
    await send_or_edit(update, f"🛍️ {t(lang,'browse')}", kb)

async def _cb_browse(update, ctx, lang, param):
    if param == "root":
        parent_id = None; title = f"🛍️ {t(lang,'browse')}"; back_data = "go_main"
    else:
        cat_id = int(param); cat = get_category(cat_id)
        if not cat:
            await send_or_edit(update, "❌", [[InlineKeyboardButton("◀️", callback_data="browse:root")]]); return
        parent_id = cat_id; title = f"📂 {get_breadcrumb(cat_id, lang)}"
        back_data = f"browse:{cat[1]}" if cat[1] else "browse:root"

    subcats  = get_categories(parent_id)
    products = get_products_in(parent_id) if parent_id else []
    kb = []
    for sc in subcats:
        total = _count_all_products(sc[0])
        kb.append([InlineKeyboardButton(f"{sc[5]}  {cat_name(sc,lang)}  ({total})", callback_data=f"browse:{sc[0]}")])
    for p in products:
        stock = get_real_stock(p)
        disc  = p[11] or 0
        icon  = "❌" if stock==0 else ("♾️" if stock==-1 else f"✅{stock}")
        disc_badge = t(lang,"disc_badge",disc=disc) if disc else ""
        price_str  = f"{p[6]*(1-disc/100):.2f}" if disc else f"{p[6]:.2f}"
        kb.append([InlineKeyboardButton(
            f"🔹  {prod_name(p,lang)}{disc_badge}  —  {price_str} USDT  [{icon}]",
            callback_data=f"prod:{p[0]}")])
    kb.append([InlineKeyboardButton(f"◀️ {t(lang,'back')}", callback_data=back_data)])
    await send_or_edit(update, title, kb)

async def _cb_product(update, ctx, lang, pid):
    p = get_product(pid)
    if not p: await update.callback_query.answer("❌ المنتج غير موجود", show_alert=True); return
    name  = prod_name(p, lang); desc = p[5] or ""
    price = p[6]; stock = get_real_stock(p); disc = p[11] or 0
    final_price = price * (1 - disc/100) if disc else price

    if stock==-1:  st = t(lang,"unlimited")
    elif stock==0: st = t(lang,"out_of_stock")
    else:          st = f"{t(lang,'available')} ({stock})"

    disc_line = f"\n🏷️ خصم {disc}% — السعر بعد الخصم: {final_price:.2f} USDT" if disc else ""
    breadcrumb = get_breadcrumb(p[1], lang)
    text = f"📂 {breadcrumb}\n{'─'*20}\n🔹 {name}\n\n{desc}\n\n💵 {price} USDT{disc_line}\n📦 {st}"
    kb = []
    if stock != 0:
        kb.append([InlineKeyboardButton(f"⚡ {t(lang,'buy_now')}",  callback_data=f"buynow:{pid}")])
    kb.append([InlineKeyboardButton(f"◀️ {t(lang,'back')}", callback_data=f"browse:{p[1]}")])
    if p[8]:
        try:
            await update.callback_query.message.reply_photo(photo=p[8], caption=text, reply_markup=InlineKeyboardMarkup(kb))
            await update.callback_query.message.delete(); return
        except: pass
    await send_or_edit(update, text, kb)

async def _show_cart(update, ctx, lang):
    uid  = update.effective_user.id; cart = get_cart(uid)
    if not cart:
        kb = [[InlineKeyboardButton(f"🛍️ {t(lang,'browse')}", callback_data="browse:root")],
              [InlineKeyboardButton(f"🏠 {t(lang,'back_main')}", callback_data="go_main")]]
        await send_or_edit(update, t(lang,"cart_empty"), kb); return

    subtotal, disc_total, final = calc_total(cart)
    lines = [f"🛒 {t(lang,'cart',n=cart_count(uid))}\n{'─'*20}"]
    kb    = []
    for pid,qty,nar,nen,nfr,price,stock,disc in cart:
        name      = nar if lang=="ar" else (nen if lang=="en" else nfr)
        eff_price = price * (1-disc/100) if disc else price
        disc_tag  = f" 🏷️-{disc}%" if disc else ""
        lines.append(f"🔹 {name}{disc_tag}\n   {qty} × {eff_price:.2f} = {qty*eff_price:.2f} USDT")
        kb.append([
            InlineKeyboardButton("➖", callback_data=f"cq:dec:{pid}"),
            InlineKeyboardButton(f" {qty} ", callback_data="noop"),
            InlineKeyboardButton("➕", callback_data=f"cq:inc:{pid}"),
            InlineKeyboardButton("🗑️", callback_data=f"cq:del:{pid}"),
        ])
    if disc_total > 0:
        lines.append(f"\n🏷️ إجمالي الخصم: -{disc_total:.2f} USDT")
    lines.append(f"\n{t(lang,'total')}: {final:.2f} USDT")
    kb.append([InlineKeyboardButton(f"🗑️ {t(lang,'clear_cart')}", callback_data="do_clear")])
    kb.append([InlineKeyboardButton(f"✅ {t(lang,'checkout')}  ──  {final:.2f} USDT", callback_data="do_checkout")])
    kb.append([InlineKeyboardButton(f"🏠 {t(lang,'back_main')}", callback_data="go_main")])
    await send_or_edit(update, "\n".join(lines), kb)

async def _show_payment(update, ctx, lang):
    uid  = update.effective_user.id; cart = get_cart(uid)
    _, _, final = calc_total(cart)
    bal = get_balance(uid)
    kb = [
        [InlineKeyboardButton(f"₿ {t(lang,'pay_heleket')}",  callback_data="pay:heleket")],
        [InlineKeyboardButton(t(lang,"pay_wallet",b=f"{bal:.2f}"), callback_data="pay:wallet")],
        [InlineKeyboardButton(f"◀️ {t(lang,'back')}",        callback_data="go_main")],
    ]
    await send_or_edit(update, f"{t(lang,'pay_title')}\n\n💰 {final:.2f} USDT", kb)

async def _cb_payment(update, ctx, lang, method):
    uid  = update.effective_user.id; cart = get_cart(uid)
    if not cart: await send_main_menu(update, ctx, lang); return
    subtotal, disc_total, final = calc_total(cart)
    items = [{"id":i[0],"qty":i[1],"name":i[2],"price":i[5]*(1-(i[7] or 0)/100)} for i in cart]

    if method == "heleket":
        oid = create_order(uid, items, final, disc_total, "heleket")
        clear_cart(uid); clear_state(uid)
        await _notify_admins(ctx, uid, update.effective_user.first_name, cart, final, "Heleket")
        pay_url = await _create_heleket_invoice(oid, final, uid)
        if pay_url:
            kb = [
                [InlineKeyboardButton("💳 ادفع الآن", url=pay_url)],
                [InlineKeyboardButton(f"📦 {t(lang,'my_orders')}", callback_data="go_orders")],
                [InlineKeyboardButton(f"🏠 {t(lang,'back_main')}", callback_data="go_main")],
            ]
            await send_or_edit(update,
                f"🔗 طلب #{oid}\n\n💰 المبلغ: {final:.2f} USDT\n⏳ صالح لـ 20 دقيقة\n\nاضغط ادفع الآن للإتمام:", kb)
        else:
            kb = [[InlineKeyboardButton(f"🏠 {t(lang,'back_main')}", callback_data="go_main")]]
            await send_or_edit(update, "❌ تعذر إنشاء رابط الدفع، تواصل مع الدعم.", kb)

    elif method == "wallet":
        bal = get_balance(uid)
        if bal < final:
            kb = [
                [InlineKeyboardButton(f"💳 {t(lang,'deposit')}", callback_data="do_deposit")],
                [InlineKeyboardButton(f"🏠 {t(lang,'back_main')}", callback_data="go_main")],
            ]
            await send_or_edit(update, t(lang,"no_balance", b=f"{bal:.2f}"), kb); return
        oid = create_order(uid, items, final, disc_total, "wallet")
        change_balance(uid, -final)
        set_order_status(oid, "completed")
        clear_cart(uid); clear_state(uid)
        await _notify_admins(ctx, uid, update.effective_user.first_name, cart, final, "Wallet")
        kb = [
            [InlineKeyboardButton(f"📦 {t(lang,'my_orders')}", callback_data="go_orders")],
            [InlineKeyboardButton(f"🏠 {t(lang,'back_main')}", callback_data="go_main")],
        ]
        await send_or_edit(update, t(lang,"order_done", id=oid), kb)
        await _deliver(ctx, uid, oid, items, lang)



async def _show_orders(update, ctx, lang):
    uid    = update.effective_user.id; orders = get_user_orders(uid)
    kb     = [[InlineKeyboardButton(f"🏠 {t(lang,'back_main')}", callback_data="go_main")]]
    if not orders: await send_or_edit(update, t(lang,"no_orders"), kb); return
    st_map = {"pending": t(lang,"pending"), "completed": t(lang,"completed"), "cancelled": t(lang,"cancelled")}
    lines  = [f"📦 {t(lang,'my_orders')}\n{'─'*20}"]
    for o in orders:
        lines.append(t(lang,"order_item", id=o[0], total=f"{o[3]:.2f}",
                       status=st_map.get(o[6],o[6]), date=o[8][:10]))
    await send_or_edit(update, "\n".join(lines), kb)

async def _show_wallet(update, ctx, lang):
    uid = update.effective_user.id
    kb  = [
        [InlineKeyboardButton(f"💳 {t(lang,'deposit')}", callback_data="do_deposit")],
        [InlineKeyboardButton(f"🏠 {t(lang,'back_main')}", callback_data="go_main")],
    ]
    await send_or_edit(update, t(lang,"wallet_info",b=f"{get_balance(uid):.2f}"), kb)

async def _show_settings(update, ctx, lang):
    kb = [
        [InlineKeyboardButton("🇸🇦 العربية", callback_data="setlang:ar"),
         InlineKeyboardButton("🇬🇧 English",  callback_data="setlang:en"),
         InlineKeyboardButton("🇫🇷 Français", callback_data="setlang:fr")],
        [InlineKeyboardButton(f"🏠 {t(lang,'back_main')}", callback_data="go_main")],
    ]
    await send_or_edit(update, "⚙️ Language / اللغة", kb)

async def _deliver(ctx, uid, oid, cart, lang):
    for item in cart:
        # يدعم كلا الشكلين: tuple من السلة المباشرة أو dict من JSON المحفوظ
        if isinstance(item, dict):
            pid = int(item["id"])
            qty = int(item["qty"])
        else:
            pid = int(item[0])
            qty = int(item[1])
        p = get_product(pid)
        if not p: continue
        name = prod_name(p, lang)
        if has_available_digital_stock(pid):
            units = stock_pop_units(pid, qty, oid)
            if not units:
                for adm in ADMIN_IDS:
                    try: await ctx.bot.send_message(adm, t("ar","out_of_stock_warn",name=name))
                    except: pass
                continue
            for i, unit in enumerate(units, 1):
                label = f"({i}/{qty}) " if qty>1 else ""
                await ctx.bot.send_message(
                    uid, t(lang,"delivered_key",id=oid,name=f"{label}{name}",key=unit), parse_mode="HTML")
            remaining = stock_count(pid)
            if 0 < remaining <= STOCK_LOW_ALERT:
                for adm in ADMIN_IDS:
                    try: await ctx.bot.send_message(adm, t("ar","stock_low_warn",name=name,count=remaining))
                    except: pass
        elif p[9]:
            await ctx.bot.send_message(
                uid, t(lang,"delivered_key",id=oid,name=name,key=p[9]), parse_mode="HTML")


import hashlib, json as _json

def _heleket_sign(body_dict):
    """توليد توقيع MD5 للـ Heleket API"""
    body_str = _json.dumps(body_dict, separators=(',', ':'), ensure_ascii=False)
    sign = hashlib.md5((
        __import__('base64').b64encode(body_str.encode()).decode()
        + HELEKET_API_KEY
    ).encode()).hexdigest()
    return body_str, sign


async def _create_heleket_invoice(order_id, amount_usd, user_id):
    """إنشاء فاتورة دفع طلب عبر Heleket API"""
    try:
        body = {
            "amount":   str(round(amount_usd, 2)),
            "currency": "USD",
            "order_id": f"order_{order_id}",
            "network":  "tron",
        }
        if HELEKET_CALLBACK_URL:
            body["url_callback"] = HELEKET_CALLBACK_URL
        body_str, sign = _heleket_sign(body)
        resp = requests.post(
            "https://api.heleket.com/v1/payment",
            headers={
                "merchant":     HELEKET_MERCHANT_ID,
                "sign":         sign,
                "Content-Type": "application/json",
            },
            data=body_str,
            timeout=10,
        )
        data = resp.json()
        result = data.get("result", {})
        return result.get("url")
    except Exception as e:
        logging.error(f"Heleket invoice error: {e}")
        return None


async def _create_heleket_deposit(amount_usd, user_id):
    """إنشاء فاتورة إيداع محفظة عبر Heleket API"""
    try:
        body = {
            "amount":   str(round(amount_usd, 2)),
            "currency": "USD",
            "order_id": f"deposit_{user_id}",
            "network":  "tron",
        }
        if HELEKET_CALLBACK_URL:
            body["url_callback"] = HELEKET_CALLBACK_URL
        body_str, sign = _heleket_sign(body)
        resp = requests.post(
            "https://api.heleket.com/v1/payment",
            headers={
                "merchant":     HELEKET_MERCHANT_ID,
                "sign":         sign,
                "Content-Type": "application/json",
            },
            data=body_str,
            timeout=10,
        )
        data = resp.json()
        result = data.get("result", {})
        return result.get("url")
    except Exception as e:
        logging.error(f"Heleket deposit error: {e}")
        return None

async def _notify_admins(ctx, uid, name, cart, total, method):
    items_txt = ", ".join([f"{i[2]}×{i[1]}" for i in cart])
    for adm in ADMIN_IDS:
        try:
            await ctx.bot.send_message(adm, t("ar","new_order_adm",
                user=f"{name}({uid})", items=items_txt, total=f"{total:.2f}", method=method))
        except: pass

# ============================================================
# ADMIN SUB-HANDLERS
# ============================================================
async def _cb_admin(update, ctx, lang, action):
    uid = update.effective_user.id

    if action == "add_cat":
        cats = get_all_categories_flat()
        kb   = [[InlineKeyboardButton(f"🌐 {t(lang,'no_parent')}", callback_data="catpar:none")]]
        for c in cats:
            dep = "  " * _cat_depth(c[0])
            kb.append([InlineKeyboardButton(f"{dep}{c[5]} {cat_name(c,lang)}", callback_data=f"catpar:{c[0]}")])
        kb.append([InlineKeyboardButton(f"◀️ {t(lang,'back_admin')}", callback_data="go_admin")])
        await send_or_edit(update, t(lang,"sel_parent"), kb)

    elif action == "add_prod":
        cats = get_all_categories_flat(); kb = []
        for c in cats:
            dep = "  " * _cat_depth(c[0])
            kb.append([InlineKeyboardButton(f"{dep}{c[5]} {cat_name(c,lang)}", callback_data=f"prodcat:{c[0]}")])
        kb.append([InlineKeyboardButton(f"◀️ {t(lang,'back_admin')}", callback_data="go_admin")])
        await send_or_edit(update, t(lang,"sel_cat_prod"), kb)

    elif action == "manage":
        kb = [
            [InlineKeyboardButton(f"🌳 {t(lang,'adm_tree')}",     callback_data="adm:tree")],
            [InlineKeyboardButton(f"✏️ {t(lang,'adm_edit_cat')}",  callback_data="adm:edit_cat"),
             InlineKeyboardButton(f"✏️ {t(lang,'adm_edit_prod')}", callback_data="adm:edit_prod")],
            [InlineKeyboardButton(f"📁 {t(lang,'adm_move_cat')}",  callback_data="adm:move_cat")],
            [InlineKeyboardButton(f"◀️ {t(lang,'back_admin')}",    callback_data="go_admin")],
        ]
        await send_or_edit(update, t(lang,"adm_manage"), kb)

    elif action == "tree":
        tree = _build_tree(lang)
        if len(tree)>4000: tree = tree[:4000]+"..."
        kb = [[InlineKeyboardButton(f"◀️ {t(lang,'back')}", callback_data="adm:manage")]]
        await send_or_edit(update, tree, kb)

    elif action == "edit_cat":
        cats = get_all_categories_flat(); kb = []
        for c in cats:
            dep    = "  " * _cat_depth(c[0])
            status = "" if c[6] else " ❌"
            kb.append([InlineKeyboardButton(f"{dep}{c[5]} {cat_name(c,lang)}{status}", callback_data=f"editcat:{c[0]}")])
        kb.append([InlineKeyboardButton(f"◀️ {t(lang,'back')}", callback_data="adm:manage")])
        await send_or_edit(update, t(lang,"sel_edit_cat"), kb)

    elif action == "edit_prod":
        cats = get_all_categories_flat(); kb = []
        for c in cats:
            for p in get_products_in(c[0]):
                status = "" if p[10] else " ❌"
                disc   = f" 🏷️{p[11]}%" if p[11] else ""
                kb.append([InlineKeyboardButton(
                    f"{c[5]} {cat_name(c,lang)} › {prod_name(p,lang)} — {p[6]}${disc}{status}",
                    callback_data=f"editprod:{p[0]}")])
        if not kb:
            await update.callback_query.answer(t(lang,"no_products"), show_alert=True)
            await reply_admin(update, ctx, lang); return
        kb.append([InlineKeyboardButton(f"◀️ {t(lang,'back')}", callback_data="adm:manage")])
        await send_or_edit(update, t(lang,"sel_edit_prod"), kb)

    elif action == "move_cat":
        cats = get_all_categories_flat(); kb = []
        for c in cats:
            dep = "  " * _cat_depth(c[0])
            kb.append([InlineKeyboardButton(f"{dep}{c[5]} {cat_name(c,lang)}", callback_data=f"movecat:{c[0]}")])
        kb.append([InlineKeyboardButton(f"◀️ {t(lang,'back')}", callback_data="adm:manage")])
        await send_or_edit(update, t(lang,"sel_edit_cat"), kb)

    elif action == "del":
        kb = [
            [InlineKeyboardButton(f"📂 {t(lang,'del_cat')}",  callback_data="adm:del_cat_list"),
             InlineKeyboardButton(f"🛍️ {t(lang,'del_prod')}", callback_data="adm:del_prod_list")],
            [InlineKeyboardButton(f"◀️ {t(lang,'back_admin')}", callback_data="go_admin")],
        ]
        await send_or_edit(update, t(lang,"sel_del"), kb)

    elif action == "del_cat_list":
        cats = get_all_categories_flat(); kb = []
        for c in cats:
            dep = "  " * _cat_depth(c[0])
            kb.append([InlineKeyboardButton(f"🗑️ {dep}{c[5]} {cat_name(c,lang)}", callback_data=f"delcat:{c[0]}")])
        kb.append([InlineKeyboardButton(f"◀️ {t(lang,'back_admin')}", callback_data="go_admin")])
        await send_or_edit(update, t(lang,"del_cat"), kb)

    elif action == "del_prod_list":
        cats = get_all_categories_flat(); kb = []
        for c in cats:
            for p in get_products_in(c[0]):
                kb.append([InlineKeyboardButton(
                    f"🗑️ {prod_name(p,lang)} ({p[6]}$)", callback_data=f"delprod:{p[0]}")])
        if not kb:
            await update.callback_query.answer(t(lang,"no_products"), show_alert=True)
            await reply_admin(update, ctx, lang); return
        kb.append([InlineKeyboardButton(f"◀️ {t(lang,'back_admin')}", callback_data="go_admin")])
        await send_or_edit(update, t(lang,"del_prod"), kb)

    elif action == "stock":
        cats = get_all_categories_flat(); kb = []
        for c in cats:
            for p in get_products_in(c[0]):
                count = stock_count(p[0]); name = prod_name(p, lang)
                kb.append([InlineKeyboardButton(f"📦 {name}  [{count} وحدة]", callback_data=f"stk:sel:{p[0]}")])
        if not kb:
            await update.callback_query.answer(t(lang,"no_products"), show_alert=True)
            await reply_admin(update, ctx, lang); return
        kb.append([InlineKeyboardButton(f"◀️ {t(lang,'back_admin')}", callback_data="go_admin")])
        await send_or_edit(update, t(lang,"sel_prod_stock"), kb)

    elif action == "discount":
        cats = get_all_categories_flat(); kb = []
        for c in cats:
            for p in get_products_in(c[0]):
                disc = p[11] or 0; name = prod_name(p, lang)
                label = f"🏷️ {name} — {p[6]}$ [{disc}%]"
                kb.append([InlineKeyboardButton(label, callback_data=f"disc:sel:{p[0]}")])
        if not kb:
            await update.callback_query.answer(t(lang,"no_products"), show_alert=True)
            await reply_admin(update, ctx, lang); return
        kb.append([InlineKeyboardButton(f"◀️ {t(lang,'back_admin')}", callback_data="go_admin")])
        await send_or_edit(update, t(lang,"disc_panel"), kb)

    elif action == "orders":
        c2 = get_conn(); cur2 = c2.cursor()
        cur2.execute("SELECT id,user_id,total,status,method,created FROM orders ORDER BY created DESC LIMIT 20")
        orders = cur2.fetchall(); c2.close()
        if not orders:
            kb = [[InlineKeyboardButton(f"◀️ {t(lang,'back_admin')}", callback_data="go_admin")]]
            await send_or_edit(update, "📋 لا توجد طلبات بعد", kb); return

        lines = ["📋 آخر الطلبات:\n" + "─"*20]
        kb    = []
        for o in orders:
            status_icon = {"pending":"⏳","completed":"✅","cancelled":"❌"}.get(o[3], "❓")
            lines.append(f"{status_icon} #{o[0]} | {o[1]} | {o[2]:.2f}$ | {o[4]} | {o[5][:10]}")
            if o[3] == "pending":
                kb.append([
                    InlineKeyboardButton(f"✅ قبول #{o[0]}", callback_data=f"approve:{o[0]}"),
                    InlineKeyboardButton(f"❌ رفض #{o[0]}",  callback_data=f"reject:{o[0]}")
                ])
        kb.append([InlineKeyboardButton(f"◀️ {t(lang,'back_admin')}", callback_data="go_admin")])
        await send_or_edit(update, "\n".join(lines), kb)

    elif action == "broadcast":
        set_state(uid, "await_broadcast", {})
        kb = [[InlineKeyboardButton(f"◀️ {t(lang,'back_admin')}", callback_data="go_admin")]]
        await send_or_edit(update, t(lang,"enter_broadcast"), kb)

    elif action == "edit_rules":
        kb = [
            [InlineKeyboardButton("🇸🇦 تعديل العربية", callback_data="editrules:ar")],
            [InlineKeyboardButton("🇬🇧 Edit English",  callback_data="editrules:en")],
            [InlineKeyboardButton("🇫🇷 Modifier FR",   callback_data="editrules:fr")],
            [InlineKeyboardButton(f"◀️ {t(lang,'back_admin')}", callback_data="go_admin")],
        ]
        current = get_rules("ar")
        await send_or_edit(update, f"📋 تعديل القوانين\n\nالنص الحالي (عربي):\n\n{current}", kb)

# ============================================================
# HELEKET WEBHOOK  (اختياري — يحتاج Flask)
# ============================================================
# ضع هذا الكود في ملف منفصل  webhook_server.py
# ثم شغّله بجانب البوت:  python3 webhook_server.py
# واضبط الرابط في HELEKET_CALLBACK_URL بالأعلى
#
# webhook_server.py:
# ─────────────────────────────────────────────────
# from flask import Flask, request, jsonify
# import hashlib, base64, json, sqlite3
# app    = Flask(__name__)
# API_KEY = "YOUR_PAYMENT_API_KEY"   # نفس HELEKET_API_KEY
# DB_PATH = "store.db"
#
# def verify_sign(data: dict, received_sign: str) -> bool:
#     body = data.copy(); body.pop("sign", None)
#     body_str = json.dumps(body, separators=(',',':'), ensure_ascii=False)
#     expected = hashlib.md5(
#         (base64.b64encode(body_str.encode()).decode() + API_KEY).encode()
#     ).hexdigest()
#     return expected == received_sign
#
# @app.route("/heleket-webhook", methods=["POST"])
# def webhook():
#     data = request.get_json(force=True)
#     if not verify_sign(data, data.get("sign","")):
#         return "Forbidden", 403
#     status   = data.get("payment_status","")
#     order_id = data.get("order_id","")
#     amount   = float(data.get("amount", 0))
#     if status in ("paid", "paid_over"):
#         conn = sqlite3.connect(DB_PATH)
#         if order_id.startswith("deposit_"):
#             uid = int(order_id.split("_")[1])
#             conn.execute("UPDATE users SET balance=balance+? WHERE id=?", (amount, uid))
#         elif order_id.startswith("order_"):
#             oid = int(order_id.split("_")[1])
#             conn.execute("UPDATE orders SET status='completed' WHERE id=?", (oid,))
#         conn.commit(); conn.close()
#     return jsonify({"status":"ok"})
#
# if __name__ == "__main__":
#     app.run(host="0.0.0.0", port=5000)
# ─────────────────────────────────────────────────

# ============================================================
# MAIN
# ============================================================
def main():
    logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', level=logging.INFO)
    print("🌐 Proxy Store Bot v4 starting...")
    init_db(); print("✅ Database ready!")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print(f"🚀 Running! Admins: {ADMIN_IDS}")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
    