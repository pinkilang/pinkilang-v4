from flask import (Flask, json, render_template_string, request, redirect, url_for, session, jsonify, send_from_directory)
from supabase import create_client, Client
from email.message import EmailMessage
from dotenv import load_dotenv
from datetime import datetime, date, timedelta
import logging
import smtplib
import random
import os
from decimal import Decimal, InvalidOperation

# ============================================================
# 🔹 Setup Logging
# ============================================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================
# 🔹 Load Konfigurasi
# ============================================================
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_APP_PASSWORD")

print("🔧 Configuration loaded:")
print(f"   SUPABASE_URL: {SUPABASE_URL}")
print(f"   SUPABASE_KEY: {SUPABASE_KEY[:20] + '...' if SUPABASE_KEY else 'NOT SET'}")
print(f"   EMAIL_SENDER: {EMAIL_SENDER}")
print(f"   EMAIL_PASSWORD: {'✅ SET' if EMAIL_PASSWORD else '❌ NOT SET'}")

# ============================================================
# 🔹 Inisialisasi Flask & Supabase 
# ============================================================
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "pinkilang_secret_123")

# Inisialisasi Supabase dengan error handling lebih baik
supabase = None
db_status = "❌ Tidak Terhubung"
db_detail = "Belum diinisialisasi"

try:
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ SUPABASE_URL atau SUPABASE_KEY tidak ditemukan di .env")
        db_status = "❌ Error"
        db_detail = "Konfigurasi Supabase tidak lengkap"
    else:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Supabase client initialized")
        
        # Test koneksi dengan cara yang lebih aman
        try:
            # Coba akses tabel user
            test_result = supabase.table("user").select("id").limit(1).execute()
            print(f"✅ Tabel user terhubung: {len(test_result.data)} data")
            db_status = "✅ Terhubung"
            db_detail = f"Tabel user siap ({len(test_result.data)} data)"
        except Exception as table_error:
            print(f"⚠️  Tabel user mungkin belum ada: {table_error}")
            db_status = "✅ Terhubung"
            db_detail = "Koneksi berhasil, tabel mungkin belum ada"
            
except Exception as e:
    print(f"❌ Supabase initialization error: {e}")
    supabase = None
    db_status = "❌ Error"
    db_detail = f"Gagal terhubung: {str(e)}"

# ============================================================
# 🔹 Fungsi Email
# ============================================================
def send_email(recipient, subject, body):
    try:
        if not EMAIL_SENDER or not EMAIL_PASSWORD:
            logger.error("❌ Konfigurasi email tidak lengkap")
            return False

        msg = EmailMessage()
        msg["From"] = EMAIL_SENDER
        msg["To"] = recipient
        msg["Subject"] = subject
        msg.set_content(body)

        logger.info(f"📧 Mengirim email ke: {recipient}")

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
        
        logger.info(f"✅ Email berhasil dikirim ke: {recipient}")
        return True
        
    except smtplib.SMTPAuthenticationError:
        logger.error("❌ Gagal autentikasi Gmail. Pastikan:")
        logger.error("1. Menggunakan App Password, bukan password biasa")
        logger.error("2. App Password 16 karakter tanpa spasi")
        logger.error("3. 2FA diaktifkan di akun Gmail")
        return False
    except Exception as e:
        logger.error(f"❌ Error mengirim email: {e}")
        return False
        
# ============================================================
# 🔹 Tampilan Base
# ============================================================
base_html = """
<!DOCTYPE html>
<html>
<head>
    <title>PINKILANG</title>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            background: linear-gradient(135deg, #ffd1dc, #ffe0e9); 
            display: flex; 
            justify-content: center; 
            align-items: center; 
            height: 100vh; 
            margin: 0; 
        }
        .container { 
            background: white; 
            padding: 30px; 
            border-radius: 15px; 
            width: 350px; 
            text-align: center; 
            box-shadow: 0 4px 12px rgba(0,0,0,0.1); 
        }
        input { 
            width: 90%; 
            padding: 10px; 
            margin: 8px 0; 
            border: 1px solid #ddd; 
            border-radius: 8px; 
            font-size: 16px;
        }
        button { 
            background: #ff66a3; 
            color: white; 
            border: none; 
            padding: 12px 24px; 
            border-radius: 8px; 
            cursor: pointer; 
            margin: 5px; 
            font-size: 16px;
            width: 95%;
        }
        button:hover {
            background: #ff4d94;
        }
        .message {
            padding: 12px;
            margin: 10px 0;
            border-radius: 8px;
            font-size: 14px;
        }
        .success { 
            background: #d4ffd4; 
            color: #006600; 
            border: 1px solid #c3e6cb;
        }
        .error { 
            background: #ffd4d4; 
            color: #cc0000; 
            border: 1px solid #f5c6cb;
        }
        .info { 
            background: #d1ecf1; 
            color: #0c5460; 
            border: 1px solid #bee5eb;
        }
        .warning { 
            background: #fff3cd; 
            color: #856404; 
            border: 1px solid #ffeaa7;
        }
        .menu { 
            margin: 15px 0; 
        }
    </style>
</head>
<body>
    <div class="container">{{ content|safe }}</div>
</body>
</html>
"""

# ============================================================
# 🔹 ROUTE: Home
# ============================================================
@app.route("/")
def home():
    try:
        if supabase:
            result = supabase.table("user").select("id", count="exact").limit(1).execute()
            current_status = "✅ Terhubung"
            current_detail = f"Tabel user aktif ({result.count} data)"
        else:
            current_status = "❌ Error"
            current_detail = "Supabase client tidak terinisialisasi"
    except Exception as e:
        current_status = "❌ Error"
        current_detail = f"Koneksi terputus: {str(e)}"

    # Cek path yang sederhana
    logo_path = 'static/image/pinkilang-logo.png'
    logo_exists = os.path.exists(logo_path)
    
    print(f"🔍 Checking logo at: {os.path.abspath(logo_path)}")
    print(f"📁 Logo exists: {logo_exists}")
    
    # Jika tidak ada, coba path alternatif
    if not logo_exists:
        # Coba path dengan backslash untuk Windows
        logo_path_win = 'static\\image\\pinkilang-logo.png'
        logo_exists = os.path.exists(logo_path_win)
        print(f"🔍 Checking Windows path: {os.path.abspath(logo_path_win)}")
        print(f"📁 Logo exists (Windows path): {logo_exists}")

    html = f"""
    <div style="text-align: center; padding: 50px 0;">
        <!-- Logo Pinkilang di Tengah -->
        <div style="margin-bottom: 40px;">
            {f'''
            <img src="/static/image/pinkilang-logo.png" 
                 alt="PINKILANG" 
                 style="max-width: 350px; width: 100%; height: auto; display: block; margin: 0 auto;">
            ''' if logo_exists else '''
            <div style="font-size: 48px; color: #ff66a3; font-weight: bold; margin-bottom: 20px;">
                PINKILANG
            </div>
            <div style="color: #666; font-size: 12px;">
                (Logo: static/image/pinkilang-logo.png tidak ditemukan)
            </div>
            '''}
        </div>
        
        <!-- Status Sistem Simple -->
        <div style="max-width: 400px; margin: 0 auto 30px; padding: 15px; background: #f8f9fa; border-radius: 8px;">
            <strong>Status Sistem:</strong><br>
            • Database: {current_status}<br>
            • {current_detail}
        </div>
        
        <!-- Tombol Aksi Simple -->
        <div style="display: flex; flex-direction: column; gap: 15px; max-width: 300px; margin: 0 auto;">
            <a href='/register' style="text-decoration: none;">
                <button style="width: 100%; padding: 12px; background: #ff66a3; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 16px;">
                    📝 Daftar
                </button>
            </a>
            <a href='/login' style="text-decoration: none;">
                <button style="width: 100%; padding: 12px; background: #6666ff; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 16px;">
                    🔐 Login
                </button>
            </a>
        </div>
    </div>
    """
    return render_template_string(base_html, content=html)

# ============================================================
# 🔹 ROUTE: Register
# ============================================================
@app.route("/register", methods=["GET", "POST"])
def register():
    message = ""
    
    if not supabase:
        message = '<div class="message error">❌ Database tidak tersedia! Silakan cek koneksi.</div>'
    
    elif request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        
        logger.info(f"🔄 Registrasi: {email}")
        
        try:
            # Cek apakah email sudah terdaftar
            result = supabase.table("user").select("email").eq("email", email).execute()
            
            if result.data:
                message = '<div class="message error">❌ Email sudah terdaftar!</div>'
                logger.warning(f"Email {email} sudah terdaftar")
            else:
                # Generate OTP
                otp = str(random.randint(100000, 999999))
                
                # Simpan data sementara di session
                session['register_email'] = email
                session['register_password'] = password
                session['register_otp'] = otp
                
                logger.info(f"📧 Kirim OTP {otp} ke {email}")
                
                # Kirim OTP via email
                email_body = f"""
                HALO! 👋

                Kode OTP Verifikasi PINKILANG Anda adalah:

                🎀 {otp} 🎀

                Masukkan kode ini di halaman verifikasi untuk menyelesaikan pendaftaran.

                Jangan berikan kode ini kepada siapapun.

                Terima kasih,
                💖 Tim PINKILANG
                """
                
                if send_email(email, "🎀 Kode OTP PINKILANG", email_body):
                    logger.info(f"✅ OTP berhasil dikirim ke {email}")
                    return redirect('/verify')
                else:
                    message = '<div class="message error">❌ Gagal kirim OTP! Cek konfigurasi email.</div>'
                    logger.error(f"❌ Gagal kirim OTP ke {email}")
                    
        except Exception as e:
            message = f'<div class="message error">⚠ Error database: {str(e)}</div>'
            logger.error(f"Database error: {str(e)}")
    
    html = f"""
    <h2>📝 Daftar Akun</h2>
    {message}
    <form method="POST">
        <input type="email" name="email" placeholder="Email" required><br>
        <input type="password" name="password" placeholder="Password" required><br>
        <button type="submit">Daftar & Kirim OTP</button>
    </form>
    <p><a href="/login">Sudah punya akun? Login</a></p>
    <a href="/"><button>🏠 Kembali</button></a>
    """
    return render_template_string(base_html, content=html)

# ============================================================
# 🔹 ROUTE: Verifikasi OTP
# ============================================================
@app.route("/verify", methods=["GET", "POST"])
def verify_otp():
    message = ""
    email = session.get('register_email')
    
    if not email:
        return redirect('/register')
    
    logger.info(f"🔄 Verifikasi OTP untuk: {email}")
    
    if request.method == "POST":
        otp_input = request.form["otp"]
        otp_session = session.get('register_otp')
        
        logger.info(f"📩 OTP input: {otp_input}, OTP session: {otp_session}")
        
        # Cek OTP
        if otp_input == otp_session:
            password = session.get('register_password')
            
            try:
                # Simpan user ke Supabase
                user_data = {
                    "email": email,
                    "password": password
                }
                
                result = supabase.table("user").insert(user_data).execute()
                logger.info(f"✅ User {email} berhasil disimpan ke database")
                
                # Hapus data sementara
                session.pop('register_email', None)
                session.pop('register_password', None)
                session.pop('register_otp', None)
                
                message = '<div class="message success">✅ Akun berhasil dibuat!</div>'
                html = f"""
                <h2>🎉 Registrasi Berhasil!</h2>
                {message}
                <p>Akun Anda sudah aktif di database.</p>
                <a href="/login"><button>🔐 Login Sekarang</button></a>
                """
                return render_template_string(base_html, content=html)
                
            except Exception as e:
                message = f'<div class="message error">❌ Gagal menyimpan ke database: {str(e)}</div>'
                logger.error(f"❌ Error simpan user: {str(e)}")
        else:
            message = '<div class="message error">❌ OTP salah! Coba lagi.</div>'
            logger.warning(f"❌ OTP salah untuk {email}")
    
    html = f"""
    <h2>🔒 Verifikasi OTP</h2>
    <p>Kode OTP dikirim ke: <strong>{email}</strong></p>
    <div class="message info">
        💡 Periksa folder <strong>Spam/Promosi</strong> jika tidak ditemukan
    </div>
    {message}
    <form method="POST">
        <input type="text" name="otp" placeholder="Masukkan 6 digit OTP" 
               required maxlength="6" pattern="[0-9]{{6}}"><br>
        <button type="submit">✅ Verifikasi</button>
    </form>
    <a href="/register"><button>↩ Kembali</button></a>
    """
    return render_template_string(base_html, content=html)

# ============================================================
# 🔹 ROUTE: Login
# ============================================================
@app.route("/login", methods=["GET", "POST"])
def login():
    message = ""
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        
        try:
            if not supabase:
                message = '<div class="message error">❌ Database tidak tersedia</div>'
            else:
                # Cek user di Supabase
                result = supabase.table("user").select("*").eq("email", email).execute()
                
                if result.data and result.data[0]['password'] == password:
                    # Login berhasil
                    session['logged_in'] = True
                    session['user_email'] = email
                    session['user_id'] = result.data[0]['id']
                    logger.info(f"✅ Login berhasil: {email}")
                    return redirect('/dashboard')
                else:
                    message = '<div class="message error">❌ Email atau password salah!</div>'
                    logger.warning(f"❌ Login gagal: {email}")
                    
        except Exception as e:
            message = f'<div class="message error">⚠ Error database: {str(e)}</div>'
            logger.error(f"Database error saat login: {str(e)}")
    
    html = f"""
    <h2>🔐 Login</h2>
    {message}
    <form method="POST">
        <input type="email" name="email" placeholder="Email" required><br>
        <input type="password" name="password" placeholder="Password" required><br>
        <button type="submit">Login</button>
    </form>
    <p><a href="/register">Belum punya akun? Daftar</a></p>
    <a href="/"><button>🏠 Kembali</button></a>
    """
    return render_template_string(base_html, content=html)

# ============================================================
# 🔹 FUNGSI: Ambil Data untuk Dashboard 
# ============================================================
def get_dashboard_data():
    """Fungsi untuk mengambil data penjualan, pembelian, dan persediaan untuk dashboard"""
    
    # Default values
    total_penjualan = 0
    total_pembelian = 0
    persediaan_saat_ini = 0
    transaksi_penjualan_terbaru = []
    transaksi_pembelian_terbaru = []
    
    try:
        if supabase:
            # 1. Ambil total penjualan
            result_penjualan = supabase.table("penjualan").select("total_penjualan").execute()
            for transaksi in result_penjualan.data:
                total_penjualan += transaksi['total_penjualan']
            
            # 2. Ambil total pembelian
            result_pembelian = supabase.table("pembelian").select("total_pembelian").execute()
            for transaksi in result_pembelian.data:
                total_pembelian += transaksi['total_pembelian']
            
            # 3. Ambil persediaan saat ini
            result_persediaan = supabase.table("persediaan_terintegrasi").select("jumlah_persediaan").eq("id", 1).execute()
            if result_persediaan.data:
                persediaan_saat_ini = result_persediaan.data[0]['jumlah_persediaan']
            
            # 4. Ambil 5 transaksi penjualan terbaru
            transaksi_penjualan_terbaru = supabase.table("penjualan").select("*").order("created_at", desc=True).limit(5).execute().data
            
            # 5. Ambil 5 transaksi pembelian terbaru
            transaksi_pembelian_terbaru = supabase.table("pembelian").select("*").order("created_at", desc=True).limit(5).execute().data
            
    except Exception as e:
        logger.error(f"❌ Error mengambil data dashboard: {str(e)}")
    
    return {
        'total_penjualan': total_penjualan,
        'total_pembelian': total_pembelian,
        'persediaan_saat_ini': persediaan_saat_ini,
        'transaksi_penjualan_terbaru': transaksi_penjualan_terbaru,
        'transaksi_pembelian_terbaru': transaksi_pembelian_terbaru
    }

# ============================================================
# 🔹 ROUTE: Dashboard
# ============================================================
@app.route("/dashboard")
def dashboard():
    if not session.get('logged_in'):
        return redirect('/login')
    
    user_email = session.get('user_email')
    
    # Ambil data user dari database
    try:
        if supabase:
            result = supabase.table("user").select("*").eq("email", user_email).execute()
            user_data = result.data[0] if result.data else {}
            user_id = user_data.get('id', 'Unknown')
        else:
            user_id = 'Database Error'
    except Exception as e:
        user_id = f'Error: {str(e)}'

    # Ambil data untuk dashboard
    dashboard_data = get_dashboard_data()
    
    total_penjualan = dashboard_data['total_penjualan']
    total_pembelian = dashboard_data['total_pembelian']
    persediaan_saat_ini = dashboard_data['persediaan_saat_ini']
    transaksi_penjualan = dashboard_data['transaksi_penjualan_terbaru']
    transaksi_pembelian = dashboard_data['transaksi_pembelian_terbaru']

    # Format currency
    def format_currency(amount):
        return f"Rp {amount:,.0f}".replace(",", ".")

    # Tampilan dashboard
    dashboard_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Dashboard PINKILANG 💖</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: 'Arial Rounded MT Bold', 'Arial', sans-serif;
                background: linear-gradient(135deg, #ffd1dc, #ffe0e9, #fff0f5);
                min-height: 100vh;
            }}
            
            .dashboard-container {{
                display: flex;
                min-height: 100vh;
            }}
            
            /* Sidebar Styles */
            .sidebar {{
                width: 250px;
                background: linear-gradient(180deg, #ff66a3, #ff4d94);
                padding: 20px;
                box-shadow: 2px 0 10px rgba(0,0,0,0.1);
            }}
            
            .logo {{
                text-align: center;
                margin-bottom: 30px;
                padding: 15px;
                background: rgba(255,255,255,0.2);
                border-radius: 15px;
                color: white;
                font-size: 24px;
                font-weight: bold;
            }}
            
            .menu-section {{
                margin-bottom: 25px;
            }}
            
            .menu-title {{
                color: white;
                font-size: 16px;
                margin-bottom: 10px;
                padding-left: 10px;
                border-left: 3px solid white;
            }}
            
            .menu-item {{
                display: block;
                width: 100%;
                padding: 12px 15px;
                margin: 5px 0;
                background: rgba(255,255,255,0.1);
                border: none;
                border-radius: 10px;
                color: white;
                text-align: left;
                cursor: pointer;
                transition: all 0.3s ease;
                font-size: 14px;
                text-decoration: none;
            }}
            
            .menu-item:hover {{
                background: rgba(255,255,255,0.3);
                transform: translateX(5px);
            }}
            
            .menu-item.active {{
                background: rgba(255,255,255,0.3);
                border-left: 3px solid white;
            }}
            
            /* Main Content Styles */
            .main-content {{
                flex: 1;
                padding: 30px;
            }}
            
            .header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 30px;
                padding: 20px;
                background: white;
                border-radius: 15px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            }}
            
            .welcome-message h1 {{
                color: #ff66a3;
                font-size: 28px;
                margin-bottom: 5px;
            }}
            
            .user-info {{
                color: #666;
                font-size: 14px;
            }}
            
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }}
            
            .stat-card {{
                background: white;
                padding: 25px;
                border-radius: 15px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                text-align: center;
                transition: transform 0.3s ease;
            }}
            
            .stat-card:hover {{
                transform: translateY(-5px);
            }}
            
            .stat-card.penjualan {{
                border-top: 5px solid #ff66a3;
            }}
            
            .stat-card.pembelian {{
                border-top: 5px solid #66b3ff;
            }}
            
            .stat-card.persediaan {{
                border-top: 5px solid #66ff99;
            }}
            
            .stat-number {{
                font-size: 36px;
                font-weight: bold;
                color: #333;
                margin: 10px 0;
            }}
            
            .stat-label {{
                color: #666;
                font-size: 14px;
            }}
            
            .content-grid {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
            }}
            
            .content-card {{
                background: white;
                padding: 25px;
                border-radius: 15px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            }}
            
            .card-title {{
                color: #ff66a3;
                font-size: 20px;
                margin-bottom: 15px;
                padding-bottom: 10px;
                border-bottom: 2px solid #ffe0e9;
            }}
            
            .transaction-list {{
                max-height: 300px;
                overflow-y: auto;
            }}
            
            .transaction-item {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 12px;
                margin: 8px 0;
                background: #f8f9fa;
                border-radius: 10px;
                border-left: 4px solid #ff66a3;
            }}
            
            .transaction-item.pembelian {{
                border-left-color: #66b3ff;
            }}
            
            .transaction-info h4 {{
                color: #333;
                margin-bottom: 5px;
                font-size: 14px;
            }}
            
            .transaction-date {{
                color: #999;
                font-size: 12px;
            }}
            
            .transaction-amount {{
                font-weight: bold;
                color: #ff66a3;
                font-size: 14px;
            }}
            
            .transaction-amount.negative {{
                color: #66b3ff;
            }}
            
            .quick-actions {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
                gap: 15px;
                margin-top: 20px;
            }}
            
            .action-btn {{
                padding: 15px;
                background: linear-gradient(135deg, #ff66a3, #ff4d94);
                color: white;
                border: none;
                border-radius: 10px;
                cursor: pointer;
                transition: all 0.3s ease;
                font-size: 14px;
                text-align: center;
                text-decoration: none;
            }}
            
            .action-btn:hover {{
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(255,102,163,0.3);
            }}
            
            .logout-btn {{
                background: linear-gradient(135deg, #ff6666, #ff4d4d);
            }}
            
            .empty-state {{
                text-align: center;
                padding: 40px 20px;
                color: #999;
            }}
            
            .user-badge {{
                background: #66b3ff;
                color: white;
                padding: 2px 6px;
                border-radius: 8px;
                font-size: 10px;
                margin-left: 5px;
            }}
            
            .current-user {{
                background: #ff66a3;
            }}
            
            /* Animations */
            @keyframes float {{
                0%, 100% {{ transform: translateY(0px); }}
                50% {{ transform: translateY(-10px); }}
            }}
            
            .floating {{
                animation: float 3s ease-in-out infinite;
            }}
        </style>
    </head>
    <body>
        <div class="dashboard-container">
            <!-- Sidebar -->
            <div class="sidebar">
                <div class="logo">
                    💖 PINKILANG
                </div>
                
                <!-- Siklus Akuntansi -->
                <div class="menu-section">
                    <div class="menu-title">📊 SIKLUS AKUNTANSI</div>
                    <a href="/jurnal-umum" class="menu-item">📝 Jurnal Umum</a>
                    <a href="/buku-besar" class="menu-item">📚 Buku Besar</a>
                    <a href="/neraca-saldo" class="menu-item">⚖ Neraca Saldo</a>
                    <a href="/jurnal-penyesuaian" class="menu-item">🔄 Jurnal Penyesuaian</a>
                    <a href="/laporan-keuangan" class="menu-item">📈 Laporan Keuangan</a>
                    <a href="/jurnal-penutup" class="menu-item">🔒 Jurnal Penutup</a>
                </div>
                
                <!-- Transaksi -->
                <div class="menu-section">
                    <div class="menu-title">💸 TRANSAKSI</div>
                    <a href="/penjualan" class="menu-item">📦Penjualan</a>
                    <a href="/pembelian" class="menu-item">🛒 Pembelian</a>
                    <a href="/operasional" class="menu-item">💰 operasional</a>
                    <a href="/buku-besar-pembantu-piutang" class="menu-item">📄 BB Pembantu Piutang</a>
                    <a href="/buku-besar-pembantu-utang" class="menu-item">📋 BB Pembantu utang</a>
                </div>
                
                <!-- Laporan -->
                <div class="menu-section">
                    <div class="menu-title">📋 LAPORAN</div>
                    <a href="/laba-rugi" class="menu-item">📊 Laba Rugi</a>
                    <a href="/neraca-saldo-setelah-penyesuaian" class="menu-item">🏦 Neraca Saldo Setelah Penyesuaian</a>
                    <a href="/neraca-lajur" class="menu-item">📈 Neraca Lajur</a>
                    <a href="/arus-kas" class="menu-item">💧 Arus Kas</a>
                    <a href="/laporan-perubahan-modal" class="menu-item">👨‍💼 Laporan Perubahan Modal</a>
                </div>
                
                <!-- Lain-lain -->
                <div class="menu-section">
                    <div class="menu-title">👥 Lain-lain</div>
                    <a href="/aset" class="menu-item"> Aset</a>
                    <a href="/prive" class="menu-item"> Prive</a>
                    <a href="/hapus-transaksi-massal" class="menu-item"> Hapus Transaksi</a>
                </div>
            </div>
            
            <!-- Main Content -->
            <div class="main-content">
                <!-- Header -->
                <div class="header">
                    <div class="welcome-message">
                        <h1>🎀 Selamat Datang, {user_email}!</h1>
                        <div class="user-info">User ID: {user_id} | Last login: {datetime.now().strftime("%d %b %Y %H:%M")}</div>
                    </div>
                    <a href="/logout" class="action-btn logout-btn">🚪 Logout</a>
                </div>
                
                <!-- Stats Grid -->
                <div class="stats-grid">
                    <div class="stat-card penjualan floating">
                        <div class="stat-icon">🛍</div>
                        <div class="stat-number">{format_currency(total_penjualan)}</div>
                        <div class="stat-label">Total Penjualan</div>
                    </div>
                    
                    <div class="stat-card pembelian floating" style="animation-delay: 0.2s">
                        <div class="stat-icon">🛒</div>
                        <div class="stat-number">{format_currency(total_pembelian)}</div>
                        <div class="stat-label">Total Pembelian</div>
                    </div>
                    
                    <div class="stat-card persediaan floating" style="animation-delay: 0.4s">
                        <div class="stat-icon">📦</div>
                        <div class="stat-number">{persediaan_saat_ini} ekor</div>
                        <div class="stat-label">Persediaan Saat Ini</div>
                    </div>
                </div>
                
                <!-- Content Grid -->
                <div class="content-grid">
                    <!-- Penjualan Terbaru -->
                    <div class="content-card">
                        <h3 class="card-title">🛍 Penjualan Terbaru</h3>
                        <div class="transaction-list">
                            {"".join([f'''
                            <div class="transaction-item">
                                <div class="transaction-info">
                                    <h4>{transaksi['nama_barang']} 
                                        <span class="user-badge {'current-user' if transaksi.get('user_email') == user_email else ''}">
                                            {transaksi.get('user_email', 'Unknown').split('@')[0]}
                                        </span>
                                    </h4>
                                    <div class="transaction-date">
                                        {datetime.strptime(transaksi['tanggal'], '%Y-%m-%d').strftime('%d %b %Y')} • {transaksi['nama_pegawai']}
                                    </div>
                                </div>
                                <div class="transaction-amount">
                                    +{format_currency(transaksi['total_penjualan'])}
                                </div>
                            </div>
                            ''' for transaksi in transaksi_penjualan]) if transaksi_penjualan else '''
                            <div class="empty-state">
                                📝 Belum ada transaksi penjualan
                            </div>
                            '''}
                        </div>
                        <a href="/penjualan" class="action-btn" style="margin-top: 15px; display: block; text-align: center;">➕ Tambah Penjualan</a>
                    </div>
                    
                    <!-- Pembelian Terbaru -->
                    <div class="content-card">
                        <h3 class="card-title">🛒 Pembelian Terbaru</h3>
                        <div class="transaction-list">
                            {"".join([f'''
                            <div class="transaction-item pembelian">
                                <div class="transaction-info">
                                    <h4>{transaksi['nama_barang']}
                                        <span class="user-badge {'current-user' if transaksi.get('user_email') == user_email else ''}">
                                            {transaksi.get('user_email', 'Unknown').split('@')[0]}
                                        </span>
                                    </h4>
                                    <div class="transaction-date">
                                        {datetime.strptime(transaksi['tanggal'], '%Y-%m-%d').strftime('%d %b %Y')} • {transaksi['nama_supplier']}
                                    </div>
                                </div>
                                <div class="transaction-amount negative">
                                    -{format_currency(transaksi['total_pembelian'])}
                                </div>
                            </div>
                            ''' for transaksi in transaksi_pembelian]) if transaksi_pembelian else '''
                            <div class="empty-state">
                                🛒 Belum ada transaksi pembelian
                            </div>
                            '''}
                        </div>
                        <a href="/pembelian" class="action-btn" style="margin-top: 15px; display: block; text-align: center;">➕ Tambah Pembelian</a>
                    </div>
                </div>
                
                <!-- Quick Actions -->
                <div class="content-card">
                    <h3 class="card-title">⚡ Aksi Cepat</h3>
                    <div class="quick-actions">
                        <a href="/penjualan" class="action-btn">🛍 Penjualan</a>
                        <a href="/pembelian" class="action-btn">🛒 Pembelian</a>
                        <a href="/kas" class="action-btn">💰 Kas</a>
                        <a href="/laporan-keuangan" class="action-btn">📊 Laporan</a>
                        <a href="/produk" class="action-btn">📦 Produk</a>
                        <a href="/pelanggan" class="action-btn">👥 Pelanggan</a>
                    </div>
                </div>
            </div>
        </div>
        
        <script>
            // Tambahkan efek interaktif
            document.addEventListener('DOMContentLoaded', function() {{
                // Highlight menu aktif
                const currentPage = window.location.pathname;
                document.querySelectorAll('.menu-item').forEach(item => {{
                    if (item.getAttribute('href') === currentPage) {{
                        item.classList.add('active');
                    }}
                }});
                
                // Animasi hover untuk stat cards
                const statCards = document.querySelectorAll('.stat-card');
                statCards.forEach(card => {{
                    card.addEventListener('mouseenter', function() {{
                        this.style.transform = 'translateY(-10px) scale(1.05)';
                    }});
                    
                    card.addEventListener('mouseleave', function() {{
                        this.style.transform = 'translateY(0px) scale(1)';
                    }});
                }});
            }});
        </script>
    </body>
    </html>
    """
    return dashboard_html

# ============================================================
# 🔹 ROUTE: Halaman Menu Lainnya
# ============================================================
def create_simple_page(title, content):
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{title} - PINKILANG</title>
        <style>
            body {{
                font-family: 'Arial Rounded MT Bold', 'Arial', sans-serif;
                background: linear-gradient(135deg, #ffd1dc, #ffe0e9);
                margin: 0;
                padding: 20px;
            }}
            .container {{
                max-width: 800px;
                margin: 0 auto;
                background: white;
                padding: 30px;
                border-radius: 20px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            }}
            h1 {{
                color: #ff66a3;
                text-align: center;
                margin-bottom: 30px;
            }}
            .back-btn {{
                display: inline-block;
                padding: 10px 20px;
                background: #ff66a3;
                color: white;
                text-decoration: none;
                border-radius: 10px;
                margin-bottom: 20px;
            }}
            .content {{
                text-align: center;
                padding: 40px 20px;
                color: #666;
                font-size: 18px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <a href="/dashboard" class="back-btn">← Kembali ke Dashboard</a>
            <h1>{title}</h1>
            <div class="content">
                {content}
            </div>
        </div>
    </body>
    </html>
    """

# ============================================================
# 🔹 KONFIGURASI AKUN (Chart of Accounts) DAFTAR AKUN
# ============================================================

CHART_OF_ACCOUNTS = {
    # Aset Lancar
    "1110": {"nama": "Kas", "tipe": "Aset Lancar", "saldo_normal": "debit"},
    "1120": {"nama": "Piutang Usaha", "tipe": "Aset Lancar", "saldo_normal": "debit"},
    "1130": {"nama": "Persediaan Barang Dagang", "tipe": "Aset Lancar", "saldo_normal": "debit"},
    "1140": {"nama": "Perlengkapan", "tipe": "Aset Lancar", "saldo_normal": "debit"},

    # Aset Tetap
    "1260": {"nama": "Akumulasi Penyusutan", "tipe": "Aset Tetap", "saldo_normal": "debit"},
    "1261": {"nama": "Tanah", "tipe": "Aset Tetap", "saldo_normal": "debit"},
    "1262": {"nama": "Bangunan", "tipe": "Aset Tetap", "saldo_normal": "debit"},
    "1263": {"nama": "Kendaraan", "tipe": "Aset Tetap", "saldo_normal": "debit"},
    "1264": {"nama": "Peralatan", "tipe": "Aset Tetap", "saldo_normal": "debit"},
    "1265": {"nama": "Inventaris", "tipe": "Aset Tetap", "saldo_normal": "debit"},

    # Utang
    "2110": {"nama": "Utang Usaha", "tipe": "Utang", "saldo_normal": "kredit"},
    "2120": {"nama": "Pendapatan Diterima Di Muka", "tipe": "Utang", "saldo_normal": "kredit"},
    
    # Modal
    "3110": {"nama": "Modal Pemilik", "tipe": "Modal", "saldo_normal": "kredit"},
    "3210": {"nama": "Prive", "tipe": "Modal", "saldo_normal": "debit"},
    "3310": {"nama": "Ikhtisar Laba Rugi", "tipe": "Modal", "saldo_normal": "debit"},

    # Pendapatan
    "4110": {"nama": "Penjualan", "tipe": "Pendapatan", "saldo_normal": "kredit"},

    # HPP
    "5110": {"nama": "Pembelian", "tipe": "HPP", "saldo_normal": "kredit"},
    "5210": {"nama": "HPP", "tipe": "HPP", "saldo_normal": "debit"},

    # Beban Operasional
    "6110": {"nama": "Beban Perlengkapan", "tipe": "Beban", "saldo_normal": "debit"},
    "6120": {"nama": "Beban TLA", "tipe": "Beban", "saldo_normal": "debit"},
    "6130": {"nama": "Beban Penyusutan", "tipe": "Beban", "saldo_normal": "debit"},
    "6140": {"nama": "Beban Lain-Lain", "tipe": "Beban", "saldo_normal": "debit"},
}
AKUN_PERSEDIAAN = "Persediaan"
AKUN_HPP = "HPP"
AKUN_PENJUALAN = "Penjualan"
AKUN_KAS = "Kas"
AKUN_PIUTANG = "Piutang"
AKUN_UTANG_USAHA = "Utang Usaha"
AKUN_BEBAN_OPERASIONAL = "Beban Operasional"
AKUN_BEBAN_PENYUSUTAN = "Beban Penyusutan"

# ============================================================
# 🎀 FUNGSI JURNAL UMUM - PINK THEME - FIXED VERSION
# ============================================================

def create_journal_entries(transaksi_type, data, user_email):
    """
    🎀 FUNGSI JURNAL - COMPATIBLE WITH EXISTING DATABASE STRUCTURE
    """
    try:
        if not supabase:
            logger.error("❌ Database tidak tersedia")
            return False
        
        # Validasi dasar
        if not data:
            logger.error("❌ Data transaksi kosong")
            return False
            
        tanggal = data.get('tanggal', datetime.now().strftime('%Y-%m-%d'))
        transaksi_id = str(data.get('transaksi_id', '')).strip()
        
        if not transaksi_id or transaksi_id.lower() == 'none':
            logger.error(f"❌ transaksi_id tidak valid: {transaksi_id}")
            return False
            
        entries = []
        
        logger.info(f"🔄 Membuat jurnal untuk {transaksi_type} ID: {transaksi_id}")
        
        if transaksi_type == "PENJUALAN":
            total_penjualan = float(data.get('total_penjualan', 0) or data.get('total', 0) or 0)
            hpp = float(data.get('hpp', 0) or data.get('harga_pokok', 0) or 0)
            metode_bayar = data.get('metode_pembayaran', 'CASH') or 'CASH'
            nama_barang = data.get('nama_barang', 'Produk') or 'Produk'
            jumlah = data.get('jumlah', 0) or 0
            nama_pelanggan = data.get('nama_pelanggan', 'Pelanggan') or 'Pelanggan'
            
            logger.info(f"📊 Processing PENJUALAN: Total={total_penjualan}, HPP={hpp}")

            if total_penjualan <= 0:
                logger.error("❌ Total penjualan harus > 0")
                return False
            
            # JURNAL UTAMA - SESUAI STRUCTURE SQL
            if metode_bayar.upper() == 'CASH':
                entries.append({
                    "tanggal": tanggal,
                    "nama_akun": "Kas",
                    "akun_debit": "Kas", 
                    "akun_kredit": "Penjualan",
                    "ref": "1110",
                    "ref_id": f"PENJUALAN_{transaksi_id}",
                    "jumlah": total_penjualan,
                    "debit": total_penjualan, 
                    "kredit": 0,
                    "keterangan": f"Penjualan tunai {nama_barang} {jumlah} unit kepada {nama_pelanggan}",
                    "transaksi_type": "PENJUALAN",
                    "transaksi_id": transaksi_id,
                    "user_email": user_email,
                    "created_at": datetime.now().isoformat()
                })
            else:
                entries.append({
                    "tanggal": tanggal,
                    "nama_akun": "Piutang Usaha",
                    "akun_debit": "Piutang Usaha",
                    "akun_kredit": "Penjualan", 
                    "ref": "1120",
                    "ref_id": f"PENJUALAN_{transaksi_id}",
                    "jumlah": total_penjualan,
                    "debit": total_penjualan,
                    "kredit": 0,
                    "keterangan": f"Piutang penjualan {nama_barang} {jumlah} unit ke {nama_pelanggan}",
                    "transaksi_type": "PENJUALAN",
                    "transaksi_id": transaksi_id,
                    "user_email": user_email,
                    "created_at": datetime.now().isoformat()
                })
            
            # ENTRI KEDUA - PENDAPATAN
            entries.append({
                "tanggal": tanggal,
                "nama_akun": "Penjualan",
                "akun_debit": "Piutang Usaha" if metode_bayar.upper() != 'CASH' else "Kas",
                "akun_kredit": "Penjualan",
                "ref": "4110", 
                "ref_id": f"PENJUALAN_{transaksi_id}",
                "jumlah": total_penjualan,
                "debit": 0,
                "kredit": total_penjualan,
                "keterangan": f"Pendapatan penjualan {nama_barang} {jumlah} unit",
                "transaksi_type": "PENJUALAN",
                "transaksi_id": transaksi_id,
                "user_email": user_email,
                "created_at": datetime.now().isoformat()
            })
            
            # JURNAL HPP (jika ada)
            if hpp > 0:
                entries.append({
                    "tanggal": tanggal,
                    "nama_akun": "Harga Pokok Penjualan",
                    "akun_debit": "Harga Pokok Penjualan",
                    "akun_kredit": "Persediaan Barang Dagang",
                    "ref": "5210",
                    "ref_id": f"PENJUALAN_{transaksi_id}",
                    "jumlah": hpp,
                    "debit": hpp,
                    "kredit": 0,
                    "keterangan": f"HPP {nama_barang} {jumlah} unit",
                    "transaksi_type": "PENJUALAN", 
                    "transaksi_id": transaksi_id,
                    "user_email": user_email,
                    "created_at": datetime.now().isoformat()
                })
                entries.append({
                    "tanggal": tanggal,
                    "nama_akun": "Persediaan Barang Dagang",
                    "akun_debit": "Harga Pokok Penjualan", 
                    "akun_kredit": "Persediaan Barang Dagang",
                    "ref": "1130",
                    "ref_id": f"PENJUALAN_{transaksi_id}",
                    "jumlah": hpp,
                    "debit": 0,
                    "kredit": hpp,
                    "keterangan": f"Pengurangan persediaan {nama_barang} {jumlah} unit",
                    "transaksi_type": "PENJUALAN",
                    "transaksi_id": transaksi_id,
                    "user_email": user_email,
                    "created_at": datetime.now().isoformat()
                })

        elif transaksi_type == "PEMBELIAN":
            total_pembelian = float(data.get('total_pembelian', 0) or data.get('total', 0) or 0)
            metode_bayar = data.get('metode_pembayaran', 'CASH') or 'CASH'
            nama_barang = data.get('nama_barang', 'Barang') or 'Barang'
            nama_supplier = data.get('nama_supplier', 'Supplier') or 'Supplier'
            jumlah = data.get('jumlah', 0) or 0
            
            logger.info(f"📊 Processing PEMBELIAN: Total={total_pembelian}")

            if total_pembelian <= 0:
                logger.error("❌ Total pembelian harus > 0")
                return False
            
            # PERSEDIAAN BERTAMBAH
            entries.append({
                "tanggal": tanggal,
                "nama_akun": "Persediaan Barang Dagang", 
                "akun_debit": "Persediaan Barang Dagang",
                "akun_kredit": "Kas" if metode_bayar.upper() == 'CASH' else "Utang Usaha",
                "ref": "1130",
                "ref_id": f"PEMBELIAN_{transaksi_id}",
                "jumlah": total_pembelian,
                "debit": total_pembelian,
                "kredit": 0,
                "keterangan": f"Pembelian {nama_barang} {jumlah} unit dari {nama_supplier}",
                "transaksi_type": "PEMBELIAN",
                "transaksi_id": transaksi_id,
                "user_email": user_email,
                "created_at": datetime.now().isoformat()
            })
            
            # SUMBER PEMBAYARAN
            if metode_bayar.upper() == 'CASH':
                entries.append({
                    "tanggal": tanggal,
                    "nama_akun": "Kas",
                    "akun_debit": "Persediaan Barang Dagang",
                    "akun_kredit": "Kas",
                    "ref": "1110",
                    "ref_id": f"PEMBELIAN_{transaksi_id}", 
                    "jumlah": total_pembelian,
                    "debit": 0,
                    "kredit": total_pembelian,
                    "keterangan": f"Pembayaran pembelian {nama_barang} ke {nama_supplier}",
                    "transaksi_type": "PEMBELIAN",
                    "transaksi_id": transaksi_id,
                    "user_email": user_email,
                    "created_at": datetime.now().isoformat()
                })
            else:
                entries.append({
                    "tanggal": tanggal,
                    "nama_akun": "Utang Usaha",
                    "akun_debit": "Persediaan Barang Dagang", 
                    "akun_kredit": "Utang Usaha",
                    "ref": "2110",
                    "ref_id": f"PEMBELIAN_{transaksi_id}",
                    "jumlah": total_pembelian,
                    "debit": 0,
                    "kredit": total_pembelian,
                    "keterangan": f"Utang pembelian {nama_barang} ke {nama_supplier}",
                    "transaksi_type": "PEMBELIAN",
                    "transaksi_id": transaksi_id,
                    "user_email": user_email,
                    "created_at": datetime.now().isoformat()
                })

        elif transaksi_type == "OPERASIONAL":
            total_pengeluaran = float(data.get('total_pengeluaran', 0) or data.get('total', 0) or 0)
            jenis_beban = data.get('jenis_pengeluaran', 'LAINNYA') or 'LAINNYA'
            metode_bayar = data.get('metode_pembayaran', 'CASH') or 'CASH'
            nama_barang = data.get('nama_barang', 'Pengeluaran') or 'Pengeluaran'
            supplier = data.get('supplier', 'Supplier') or 'Supplier'
            
            logger.info(f"📊 Processing OPERASIONAL: Total={total_pengeluaran}")

            if total_pengeluaran <= 0:
                logger.error("❌ Total pengeluaran harus > 0")
                return False
            
            # MAPPING JENIS BEBAN
            beban_map = {
                'PERLENGKAPAN': {'nama': 'Beban Perlengkapan', 'ref': '6110'},
                'LISTRIK': {'nama': 'Beban Listrik', 'ref': '6140'},
                'SEWA': {'nama': 'Beban Sewa', 'ref': '6130'}, 
                'GAJI': {'nama': 'Beban Gaji', 'ref': '6120'},
                'LAINNYA': {'nama': 'Beban Lainnya', 'ref': '6170'}
            }
            beban_info = beban_map.get(jenis_beban, beban_map['LAINNYA'])
            
            # BEBAN BERTAMBAH
            entries.append({
                "tanggal": tanggal,
                "nama_akun": beban_info['nama'],
                "akun_debit": beban_info['nama'],
                "akun_kredit": "Kas" if metode_bayar.upper() == 'CASH' else "Utang Usaha",
                "ref": beban_info['ref'],
                "ref_id": f"OPERASIONAL_{transaksi_id}",
                "jumlah": total_pengeluaran,
                "debit": total_pengeluaran,
                "kredit": 0,
                "keterangan": f"{beban_info['nama']} - {nama_barang} dari {supplier}",
                "transaksi_type": "OPERASIONAL",
                "transaksi_id": transaksi_id,
                "user_email": user_email,
                "created_at": datetime.now().isoformat()
            })
            
            # SUMBER PEMBAYARAN
            entries.append({
                "tanggal": tanggal,
                "nama_akun": "Kas" if metode_bayar.upper() == 'CASH' else "Utang Usaha",
                "akun_debit": beban_info['nama'],
                "akun_kredit": "Kas" if metode_bayar.upper() == 'CASH' else "Utang Usaha", 
                "ref": "1110" if metode_bayar.upper() == 'CASH' else "2110",
                "ref_id": f"OPERASIONAL_{transaksi_id}",
                "jumlah": total_pengeluaran,
                "debit": 0,
                "kredit": total_pengeluaran,
                "keterangan": f"Pembayaran {beban_info['nama'].lower()} - {nama_barang}",
                "transaksi_type": "OPERASIONAL",
                "transaksi_id": transaksi_id,
                "user_email": user_email,
                "created_at": datetime.now().isoformat()
            })

        elif transaksi_type == "PRIVE":
            jumlah = float(data.get('jumlah', 0) or data.get('total', 0) or 0)
            keterangan = data.get('keterangan', 'Pengambilan prive') or 'Pengambilan prive'
            
            logger.info(f"📊 Processing PRIVE: Jumlah={jumlah}")

            if jumlah <= 0:
                logger.error("❌ Jumlah prive harus > 0")
                return False
            
            entries.extend([
                {
                    "tanggal": tanggal,
                    "nama_akun": "Prive",
                    "akun_debit": "Prive",
                    "akun_kredit": "Kas",
                    "ref": "3210",
                    "ref_id": f"PRIVE_{transaksi_id}",
                    "jumlah": jumlah,
                    "debit": jumlah,
                    "kredit": 0,
                    "keterangan": f"Pengambilan prive: {keterangan}",
                    "transaksi_type": "PRIVE",
                    "transaksi_id": transaksi_id,
                    "user_email": user_email,
                    "created_at": datetime.now().isoformat()
                },
                {
                    "tanggal": tanggal,
                    "nama_akun": "Kas",
                    "akun_debit": "Prive", 
                    "akun_kredit": "Kas",
                    "ref": "1110",
                    "ref_id": f"PRIVE_{transaksi_id}",
                    "jumlah": jumlah,
                    "debit": 0,
                    "kredit": jumlah,
                    "keterangan": f"Pembayaran prive: {keterangan}",
                    "transaksi_type": "PRIVE",
                    "transaksi_id": transaksi_id,
                    "user_email": user_email,
                    "created_at": datetime.now().isoformat()
                }
            ])

        elif transaksi_type == "TAMBAHAN_MODAL":
            jumlah = float(data.get('jumlah', 0) or data.get('total', 0) or 0)
            keterangan = data.get('keterangan', 'Tambahan modal') or 'Tambahan modal'
            
            logger.info(f"📊 Processing TAMBAHAN_MODAL: Jumlah={jumlah}")

            if jumlah <= 0:
                logger.error("❌ Jumlah modal harus > 0")
                return False
            
            entries.extend([
                {
                    "tanggal": tanggal,
                    "nama_akun": "Kas",
                    "akun_debit": "Kas",
                    "akun_kredit": "Modal Pemilik", 
                    "ref": "1110",
                    "ref_id": f"MODAL_{transaksi_id}",
                    "jumlah": jumlah,
                    "debit": jumlah,
                    "kredit": 0,
                    "keterangan": f"Setoran modal: {keterangan}",
                    "transaksi_type": "TAMBAHAN_MODAL",
                    "transaksi_id": transaksi_id,
                    "user_email": user_email,
                    "created_at": datetime.now().isoformat()
                },
                {
                    "tanggal": tanggal,
                    "nama_akun": "Modal Pemilik",
                    "akun_debit": "Kas",
                    "akun_kredit": "Modal Pemilik",
                    "ref": "3110",
                    "ref_id": f"MODAL_{transaksi_id}",
                    "jumlah": jumlah,
                    "debit": 0,
                    "kredit": jumlah,
                    "keterangan": f"Tambahan modal: {keterangan}",
                    "transaksi_type": "TAMBAHAN_MODAL",
                    "transaksi_id": transaksi_id,
                    "user_email": user_email,
                    "created_at": datetime.now().isoformat()
                }
            ])

        # 💾 SIMPAN KE DATABASE
        success_count = 0
        if not entries:
            logger.warning("⚠️ Tidak ada entri jurnal yang dibuat")
            return False
            
        for entry in entries:
            try:
                # Validasi minimal
                if not entry.get('nama_akun'):
                    continue
                    
                result = supabase.table("jurnal_umum").insert(entry).execute()
                if result.data:
                    success_count += 1
                    logger.info(f"✅ Jurnal: {entry['nama_akun']} - {entry['debit']}/{entry['kredit']}")
                else:
                    logger.error(f"❌ Gagal: {result.error}")
            except Exception as e:
                logger.error(f"❌ Exception: {str(e)}")
                continue
        
        logger.info(f"🎀 {success_count}/{len(entries)} jurnal berhasil")
        return success_count > 0
        
    except Exception as e:
        logger.error(f"❌ Error create_journal_entries: {str(e)}")
        return False


# ============================================================
# 🎀 ROUTE: Generate Jurnal Otomatis - PINK THEME
# ============================================================

@app.route("/generate-jurnal-otomatis")
def generate_jurnal_otomatis():
    """Generate jurnal dari SEMUA transaksi - PINK THEME"""
    if not session.get('logged_in'):
        return redirect('/login')
    
    user_email = session.get('user_email')
    success_count = 0
    total_processed = 0
    error_messages = []
    
    try:
        logger.info(f"🎀 Memulai generate jurnal otomatis oleh {user_email}")
        
        # 🎯 1. GENERATE DARI PENJUALAN
        try:
            result = supabase.table("penjualan").select("*").execute()
            penjualan_data = result.data if result else []
            logger.info(f"📊 Found {len(penjualan_data)} penjualan records")
            
            for penjualan in penjualan_data:
                total_processed += 1
                penjualan_id = str(penjualan.get('id', ''))
                
                # Cek apakah sudah ada jurnal
                existing = supabase.table("jurnal_umum").select("*").eq("transaksi_id", penjualan_id).eq("transaksi_type", "PENJUALAN").execute()
                
                if not existing.data:  
                    # Buat data jurnal
                    journal_data = {
                        'tanggal': penjualan.get('tanggal', datetime.now().strftime('%Y-%m-%d')),
                        'nama_barang': penjualan.get('nama_barang', 'Produk'),
                        'jumlah': penjualan.get('jumlah', 0),
                        'total_penjualan': float(penjualan.get('total_penjualan', 0)),
                        'hpp': float(penjualan.get('hpp', 0)),
                        'metode_pembayaran': penjualan.get('metode_pembayaran', 'CASH'),
                        'nama_pelanggan': penjualan.get('nama_pelanggan', 'Pelanggan'),
                        'transaksi_id': penjualan_id
                    }
                    
                    if create_journal_entries("PENJUALAN", journal_data, user_email):
                        success_count += 1
                        logger.info(f"✅ Jurnal dibuat untuk penjualan ID: {penjualan_id}")
                    else:
                        error_msg = f"Gagal buat jurnal untuk penjualan ID: {penjualan_id}"
                        error_messages.append(error_msg)
                        logger.error(f"❌ {error_msg}")
                else:
                    logger.info(f"⏭️ Penjualan ID {penjualan_id} sudah memiliki jurnal")
        except Exception as e:
            error_msg = f"Error proses penjualan: {str(e)}"
            error_messages.append(error_msg)
            logger.error(f"❌ {error_msg}")
        
        # 🎯 2. GENERATE DARI PEMBELIAN
        try:
            result = supabase.table("pembelian").select("*").execute()
            pembelian_data = result.data if result else []
            logger.info(f"📊 Found {len(pembelian_data)} pembelian records")
            
            for pembelian in pembelian_data:
                total_processed += 1
                pembelian_id = str(pembelian.get('id', ''))
                
                existing = supabase.table("jurnal_umum").select("*").eq("transaksi_id", pembelian_id).eq("transaksi_type", "PEMBELIAN").execute()
                
                if not existing.data:
                    journal_data = {
                        'tanggal': pembelian.get('tanggal', datetime.now().strftime('%Y-%m-%d')),
                        'nama_barang': pembelian.get('nama_barang', 'Barang'),
                        'jumlah': pembelian.get('jumlah', 0),
                        'total_pembelian': float(pembelian.get('total_pembelian', 0)),
                        'metode_pembayaran': pembelian.get('metode_pembayaran', 'CASH'),
                        'nama_supplier': pembelian.get('nama_supplier', 'Supplier'),
                        'transaksi_id': pembelian_id
                    }
                    
                    if create_journal_entries("PEMBELIAN", journal_data, user_email):
                        success_count += 1
                        logger.info(f"✅ Jurnal dibuat untuk pembelian ID: {pembelian_id}")
                    else:
                        error_msg = f"Gagal buat jurnal untuk pembelian ID: {pembelian_id}"
                        error_messages.append(error_msg)
                        logger.error(f"❌ {error_msg}")
                else:
                    logger.info(f"⏭️ Pembelian ID {pembelian_id} sudah memiliki jurnal")
        except Exception as e:
            error_msg = f"Error proses pembelian: {str(e)}"
            error_messages.append(error_msg)
            logger.error(f"❌ {error_msg}")
        
        # 🎯 3. GENERATE DARI OPERASIONAL
        try:
            result = supabase.table("operasional").select("*").execute()
            operasional_data = result.data if result else []
            logger.info(f"📊 Found {len(operasional_data)} operasional records")
            
            for operasional in operasional_data:
                total_processed += 1
                operasional_id = str(operasional.get('id', ''))
                
                existing = supabase.table("jurnal_umum").select("*").eq("transaksi_id", operasional_id).eq("transaksi_type", "OPERASIONAL").execute()
                
                if not existing.data:
                    journal_data = {
                        'tanggal': operasional.get('tanggal', datetime.now().strftime('%Y-%m-%d')),
                        'jenis_pengeluaran': operasional.get('jenis_pengeluaran', 'LAINNYA'),
                        'nama_barang': operasional.get('nama_barang', 'Pengeluaran'),
                        'total_pengeluaran': float(operasional.get('total_pengeluaran', 0)),
                        'metode_pembayaran': operasional.get('metode_pembayaran', 'CASH'),
                        'supplier': operasional.get('supplier', 'Supplier'),
                        'transaksi_id': operasional_id
                    }
                    
                    if create_journal_entries("OPERASIONAL", journal_data, user_email):
                        success_count += 1
                        logger.info(f"✅ Jurnal dibuat untuk operasional ID: {operasional_id}")
                    else:
                        error_msg = f"Gagal buat jurnal untuk operasional ID: {operasional_id}"
                        error_messages.append(error_msg)
                        logger.error(f"❌ {error_msg}")
                else:
                    logger.info(f"⏭️ Operasional ID {operasional_id} sudah memiliki jurnal")
        except Exception as e:
            error_msg = f"Error proses operasional: {str(e)}"
            error_messages.append(error_msg)
            logger.error(f"❌ {error_msg}")
        
        # 🎯 4. GENERATE DARI PRIVE
        try:
            result = supabase.table("prive").select("*").execute()
            prive_data = result.data if result else []
            logger.info(f"📊 Found {len(prive_data)} prive records")
            
            for prive in prive_data:
                total_processed += 1
                prive_id = str(prive.get('id', ''))
                
                existing = supabase.table("jurnal_umum").select("*").eq("transaksi_id", prive_id).eq("transaksi_type", "PRIVE").execute()
                
                if not existing.data:
                    journal_data = {
                        'tanggal': prive.get('tanggal', datetime.now().strftime('%Y-%m-%d')),
                        'jumlah': float(prive.get('jumlah', 0)),
                        'keterangan': prive.get('keterangan', 'Pengambilan prive'),
                        'metode_pembayaran': prive.get('metode_pembayaran', 'CASH'),
                        'transaksi_id': prive_id
                    }
                    
                    if create_journal_entries("PRIVE", journal_data, user_email):
                        success_count += 1
                        logger.info(f"✅ Jurnal dibuat untuk prive ID: {prive_id}")
                    else:
                        error_msg = f"Gagal buat jurnal untuk prive ID: {prive_id}"
                        error_messages.append(error_msg)
                        logger.error(f"❌ {error_msg}")
                else:
                    logger.info(f"⏭️ Prive ID {prive_id} sudah memiliki jurnal")
        except Exception as e:
            error_msg = f"Error proses prive: {str(e)}"
            error_messages.append(error_msg)
            logger.error(f"❌ {error_msg}")
        
        # 🎯 5. GENERATE DARI MODAL
        try:
            result = supabase.table("modal").select("*").eq("tipe", "TAMBAHAN_MODAL").execute()
            modal_data = result.data if result else []
            logger.info(f"📊 Found {len(modal_data)} modal records")
            
            for modal in modal_data:
                total_processed += 1
                modal_id = str(modal.get('id', ''))
                
                existing = supabase.table("jurnal_umum").select("*").eq("transaksi_id", modal_id).eq("transaksi_type", "TAMBAHAN_MODAL").execute()
                
                if not existing.data:
                    journal_data = {
                        'tanggal': modal.get('tanggal', datetime.now().strftime('%Y-%m-%d')),
                        'jumlah': float(modal.get('jumlah', 0)),
                        'keterangan': modal.get('keterangan', 'Tambahan modal'),
                        'sumber_modal': modal.get('sumber_modal', 'CASH'),
                        'transaksi_id': modal_id
                    }
                    
                    if create_journal_entries("TAMBAHAN_MODAL", journal_data, user_email):
                        success_count += 1
                        logger.info(f"✅ Jurnal dibuat untuk modal ID: {modal_id}")
                    else:
                        error_msg = f"Gagal buat jurnal untuk modal ID: {modal_id}"
                        error_messages.append(error_msg)
                        logger.error(f"❌ {error_msg}")
                else:
                    logger.info(f"⏭️ Modal ID {modal_id} sudah memiliki jurnal")
        except Exception as e:
            error_msg = f"Error proses modal: {str(e)}"
            error_messages.append(error_msg)
            logger.error(f"❌ {error_msg}")
        
        logger.info(f"🎀 Generate selesai: {success_count}/{total_processed} berhasil")
        
        # Tampilkan pesan hasil
        if success_count > 0:
            session['flash_message'] = f"🎀 Berhasil membuat {success_count} jurnal dari {total_processed} transaksi!"
        else:
            if total_processed > 0:
                session['flash_message'] = f"💖 Semua {total_processed} transaksi sudah memiliki jurnal"
            else:
                session['flash_message'] = "🌸 Tidak ada transaksi yang ditemukan"
        
        if error_messages:
            session['flash_message'] += f"<br>⚠️ {len(error_messages)} error: {', '.join(error_messages[:2])}"
        
    except Exception as e:
        logger.error(f"❌ Error generate jurnal: {str(e)}")
        session['flash_message'] = f"❌ Error sistem: {str(e)}"
    
    return redirect('/jurnal-umum')


# ============================================================
# 🎀 ROUTE: Jurnal Umum - PINK SOFT THEME
# ============================================================

@app.route("/jurnal-umum")
def jurnal_umum():
    if not session.get('logged_in'):
        return redirect('/login')

    user_email = session.get('user_email')
    flash_message = session.pop('flash_message', None)
    
    try:
        # Ambil data jurnal
        result = supabase.table("jurnal_umum").select("*").order("tanggal", desc=True).order("created_at", desc=True).execute()
        jurnal_data = result.data if result else []
        
        # Filter hanya yang valid
        jurnal_data = [j for j in jurnal_data if j.get('nama_akun')]
        
        logger.info(f"📊 Loaded {len(jurnal_data)} jurnal records")
        
    except Exception as e:
        logger.error(f"Error ambil jurnal: {str(e)}")
        jurnal_data = []

    # Hitung totals
    total_debit = sum((float(j.get("debit")) if j.get("debit") else 0) for j in jurnal_data)
    total_kredit = sum((float(j.get("kredit")) if j.get("kredit") else 0) for j in jurnal_data)

    # Format currency
    def format_currency(val):
        try:
            if val is None or val == 0:
                return "Rp 0"
            return f"Rp {float(val):,.0f}".replace(",", ".")
        except:
            return "Rp 0"

    # Generate table rows
    rows_html = ""
    if jurnal_data:
        for j in jurnal_data:
            tanggal = j.get("tanggal", "")
            try:
                if isinstance(tanggal, str) and "-" in tanggal:
                    parts = tanggal.split("-")
                    if len(parts) == 3:
                        tanggal_fmt = f"{parts[2]}/{parts[1]}/{parts[0]}"
                    else:
                        tanggal_fmt = tanggal
                else:
                    tanggal_fmt = str(tanggal)
            except:
                tanggal_fmt = str(tanggal)
            
            nama_akun = j.get('nama_akun', 'Tidak Diketahui')
            ref = j.get('ref', '-')
            keterangan = j.get('keterangan', 'Tidak ada keterangan')
            transaksi_type = j.get('transaksi_type', 'General')
            user_email_jurnal = j.get('user_email', 'System')
            transaksi_id = j.get('transaksi_id', '')
            
            debit_val = j.get('debit') or 0
            kredit_val = j.get('kredit') or 0
            
            debit_class = "debit" if debit_val and float(debit_val) > 0 else ""
            kredit_class = "kredit" if kredit_val and float(kredit_val) > 0 else ""
            
            rows_html += f"""
                <tr>
                    <td>{tanggal_fmt}</td>
                    <td><strong>{nama_akun}</strong></td>
                    <td>{ref}</td>
                    <td class="{debit_class}">{format_currency(debit_val) if debit_val and float(debit_val) > 0 else '-'}</td>
                    <td class="{kredit_class}">{format_currency(kredit_val) if kredit_val and float(kredit_val) > 0 else '-'}</td>
                    <td>{keterangan}</td>
                    <td>
                        <span class="transaksi-badge">{transaksi_type}</span>
                        <br><small>{user_email_jurnal}</small>
                    </td>
                </tr>
            """
    else:
        rows_html = """
            <tr>
                <td colspan="7" class="empty-state">
                    <div style="text-align: center; padding: 40px;">
                        <h3 style="color: #666; margin-bottom: 20px;">🌸 Belum ada entri jurnal</h3>
                        <p style="color: #888; margin-bottom: 30px;">Mulai dengan membuat transaksi atau generate jurnal otomatis</p>
                        <a href="/generate-jurnal-otomatis" class="btn-generate">
                            🎀 GENERATE JURNAL OTOMATIS
                        </a>
                    </div>
                </td>
            </tr>
        """

    # Balance check
    selisih = abs(total_debit - total_kredit)
    is_balanced = selisih < 0.01
    
    # Flash message
    flash_html = ""
    if flash_message:
        flash_type = "success" if "Berhasil" in flash_message or "Semua" in flash_message or "Tidak ada" in flash_message else "error"
        flash_html = f'<div class="flash-message {flash_type}">{flash_message}</div>'

    # 🎀 PINK SOFT THEME HTML
    html = f"""
    <!DOCTYPE html>
    <html lang="id">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Jurnal Umum - PINKILANG</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #ffafbd 0%, #ffc3a0 100%);
                min-height: 100vh;
                padding: 20px;
            }}
            
            .container {{
                max-width: 1400px;
                margin: 0 auto;
                background: rgba(255, 255, 255, 0.95);
                border-radius: 20px;
                box-shadow: 0 20px 40px rgba(255, 182, 193, 0.3);
                overflow: hidden;
                backdrop-filter: blur(10px);
            }}
            
            .header {{
                background: linear-gradient(135deg, #ff758c 0%, #ff7eb3 100%);
                color: white;
                padding: 30px;
                text-align: center;
                position: relative;
            }}
            
            .back-btn {{
                position: absolute;
                left: 30px;
                top: 30px;
                padding: 12px 20px;
                background: rgba(255, 255, 255, 0.2);
                color: white;
                text-decoration: none;
                border-radius: 10px;
                border: 1px solid rgba(255, 255, 255, 0.3);
                transition: all 0.3s ease;
            }}
            
            .back-btn:hover {{
                background: rgba(255, 255, 255, 0.3);
                transform: translateY(-2px);
            }}
            
            .header h1 {{
                font-size: 2.5rem;
                margin-bottom: 10px;
                font-weight: 700;
            }}
            
            .header p {{
                font-size: 1.1rem;
                opacity: 0.9;
            }}
            
            .content {{
                padding: 30px;
            }}
            
            .flash-message {{
                padding: 20px;
                margin-bottom: 25px;
                border-radius: 15px;
                text-align: center;
                font-weight: 600;
                font-size: 1.1rem;
                box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            }}
            
            .flash-message.success {{
                background: linear-gradient(135deg, #a8e6cf, #dcedc1);
                color: #2d5016;
                border-left: 5px solid #7bc043;
            }}
            
            .flash-message.error {{
                background: linear-gradient(135deg, #ffaaa5, #ff8b94);
                color: #8b0000;
                border-left: 5px solid #ff6b6b;
            }}
            
            .summary-cards {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
                margin-bottom: 30px;
            }}
            
            .summary-card {{
                background: linear-gradient(135deg, #ffb6c1, #ffacc5);
                color: white;
                padding: 25px;
                border-radius: 20px;
                text-align: center;
                box-shadow: 0 8px 25px rgba(255, 182, 193, 0.4);
                transition: transform 0.3s ease;
            }}
            
            .summary-card:hover {{
                transform: translateY(-5px);
            }}
            
            .summary-card h3 {{
                font-size: 1.2rem;
                margin-bottom: 15px;
                opacity: 0.9;
            }}
            
            .summary-number {{
                font-size: 2.5rem;
                font-weight: bold;
                margin: 10px 0;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
            }}
            
            .balance-check {{
                padding: 20px;
                margin: 25px 0;
                border-radius: 15px;
                text-align: center;
                font-weight: bold;
                font-size: 1.2rem;
                box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            }}
            
            .balanced {{
                background: linear-gradient(135deg, #a8e6cf, #dcedc1);
                color: #2d5016;
                border-left: 5px solid #7bc043;
            }}
            
            .not-balanced {{
                background: linear-gradient(135deg, #ffaaa5, #ff8b94);
                color: #8b0000;
                border-left: 5px solid #ff6b6b;
            }}
            
            .table-container {{
                background: white;
                border-radius: 20px;
                overflow: hidden;
                box-shadow: 0 10px 30px rgba(255, 182, 193, 0.2);
                margin: 30px 0;
                overflow-x: auto;
                border: 1px solid #ffe4e9;
            }}
            
            table {{
                width: 100%;
                border-collapse: collapse;
                min-width: 1000px;
            }}
            
            th {{
                background: linear-gradient(135deg, #ff758c, #ff7eb3);
                color: white;
                padding: 18px 15px;
                text-align: left;
                font-weight: 600;
                font-size: 1rem;
            }}
            
            td {{
                padding: 16px 15px;
                border-bottom: 1px solid #ffe4e9;
                font-size: 0.95rem;
            }}
            
            tr:hover {{
                background: #fff5f7;
                transform: translateY(-1px);
                transition: all 0.2s ease;
            }}
            
            .debit {{
                color: #27ae60;
                font-weight: bold;
                font-size: 1.1rem;
            }}
            
            .kredit {{
                color: #e74c3c;
                font-weight: bold;
                font-size: 1.1rem;
            }}
            
            .transaksi-badge {{
                background: #ffeaa7;
                color: #e17055;
                padding: 6px 12px;
                border-radius: 20px;
                font-size: 0.8rem;
                font-weight: bold;
                display: inline-block;
            }}
            
            .action-buttons {{
                display: flex;
                justify-content: center;
                gap: 15px;
                flex-wrap: wrap;
                margin-top: 30px;
            }}
            
            .btn {{
                padding: 14px 28px;
                border: none;
                border-radius: 15px;
                font-size: 1rem;
                font-weight: 600;
                cursor: pointer;
                text-decoration: none;
                display: inline-flex;
                align-items: center;
                gap: 8px;
                transition: all 0.3s ease;
                box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            }}
            
            .btn:hover {{
                transform: translateY(-3px);
                box-shadow: 0 8px 25px rgba(0,0,0,0.15);
            }}
            
            .btn-danger {{
                background: linear-gradient(135deg, #ff758c, #ff7eb3);
                color: white;
            }}
            
            .btn-primary {{
                background: linear-gradient(135deg, #ffb6c1, #ffacc5);
                color: white;
            }}
            
            .btn-secondary {{
                background: linear-gradient(135deg, #a8e6cf, #dcedc1);
                color: #2d5016;
            }}
            
            .empty-state {{
                text-align: center;
                padding: 60px 20px;
                color: #888;
            }}
            
            .btn-generate {{
                background: linear-gradient(135deg, #ff758c, #ff7eb3);
                color: white;
                padding: 15px 30px;
                border-radius: 15px;
                text-decoration: none;
                font-weight: bold;
                display: inline-block;
                transition: all 0.3s ease;
                box-shadow: 0 4px 15px rgba(255, 107, 107, 0.3);
            }}
            
            .btn-generate:hover {{
                transform: translateY(-3px);
                box-shadow: 0 8px 25px rgba(255, 107, 107, 0.4);
            }}
            
            @media (max-width: 768px) {{
                .summary-cards {{
                    grid-template-columns: 1fr;
                }}
                
                .action-buttons {{
                    flex-direction: column;
                    align-items: center;
                }}
                
                .btn {{
                    width: 100%;
                    max-width: 300px;
                    justify-content: center;
                }}
                
                th, td {{
                    padding: 12px 8px;
                    font-size: 0.9rem;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <a href="/dashboard" class="back-btn">← Dashboard</a>
                <h1>📝 Jurnal Umum</h1>
                <p>Sistem Pencatatan Double Entry - PINKILANG Accounting</p>
            </div>
            
            <div class="content">
                {flash_html}
                
                <div class="summary-cards">
                    <div class="summary-card">
                        <h3>💰 Total Debit</h3>
                        <div class="summary-number">{format_currency(total_debit)}</div>
                        <p>Total semua transaksi debit</p>
                    </div>
                    <div class="summary-card">
                        <h3>💳 Total Kredit</h3>
                        <div class="summary-number">{format_currency(total_kredit)}</div>
                        <p>Total semua transaksi kredit</p>
                    </div>
                </div>
                
                <div class="balance-check {'balanced' if is_balanced else 'not-balanced'}">
                    {'🌸 JURNAL SEIMBANG' if is_balanced else '🎀 JURNAL TIDAK SEIMBANG'}
                    {f'<br><small style="opacity: 0.8;">Selisih: {format_currency(selisih)}</small>' if not is_balanced else ''}
                </div>
                
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>Tanggal</th>
                                <th>Akun</th>
                                <th>Ref</th>
                                <th>Debit</th>
                                <th>Kredit</th>
                                <th>Keterangan</th>
                                <th>Info</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows_html}
                        </tbody>
                    </table>
                </div>
                
                <div class="action-buttons">
                    <a href="/generate-jurnal-otomatis" class="btn btn-danger">
                        🎀 Generate Jurnal Otomatis
                    </a>
                    <a href="/penjualan" class="btn btn-primary">🛍️ Input Penjualan</a>
                    <a href="/pembelian" class="btn btn-primary">🛒 Input Pembelian</a>
                    <a href="/operasional" class="btn btn-primary">💰 Input Operasional</a>
                    <a href="/prive" class="btn btn-secondary">💼 Input Prive</a>
                </div>
            </div>
        </div>
        
        <script>
            // Auto refresh flash message
            setTimeout(() => {{
                const flashMsg = document.querySelector('.flash-message');
                if (flashMsg) {{
                    flashMsg.style.opacity = '0';
                    flashMsg.style.transition = 'opacity 0.5s ease';
                    setTimeout(() => flashMsg.remove(), 500);
                }}
            }}, 5000);
        </script>
    </body>
    </html>
    """
    return html


# ============================================================
# 🎀 ROUTE: Fix Jurnal Problem
# ============================================================

@app.route("/fix-jurnal-problem")
def fix_jurnal_problem():
    """Route untuk fix masalah jurnal"""
    if not session.get('logged_in'):
        return redirect('/login')
    
    try:
        # 1. Hapus jurnal yang corrupt
        supabase.table("jurnal_umum").delete().is_("nama_akun", "null").execute()
        supabase.table("jurnal_umum").delete().eq("nama_akun", "None").execute()
        supabase.table("jurnal_umum").delete().eq("nama_akun", "").execute()
        
        # 2. Reset untuk testing
        session['flash_message'] = "🎀 Masalah jurnal sudah difixed. Silakan generate ulang."
        
    except Exception as e:
        session['flash_message'] = f"❌ Error fix: {str(e)}"
    
    return redirect('/jurnal-umum')

# ============================================================
# 🔹 ROUTE: Penjualan
# ============================================================
@app.route("/penjualan", methods=["GET", "POST"])
def penjualan():
    if not session.get('logged_in'):
        return redirect('/login')
    
    user_id = session.get('user_id')
    user_email = session.get('user_email')
    message = ""
    
   # Harga pembelian tetap per ekor
    HARGA_BELI_1 = 200  # Rp 200 per ekor
    HARGA_BELI_2 = 500  # Rp 500 per ekor

    # Handle form submission untuk transaksi penjualan
    if request.method == "POST" and 'add_penjualan' in request.form:
        tanggal = request.form["tanggal"]
        nama_barang = request.form["nama_barang"]
        nama_pegawai = request.form["nama_pegawai"]
        jumlah = int(request.form["jumlah"])
        tipe_harga = request.form["tipe_harga"]
        harga_jual = int(request.form["harga_jual"])
        metode_pembayaran = request.form["metode_pembayaran"]
        nama_pelanggan = request.form.get("nama_pelanggan", "")
        
        # Validasi untuk penjualan kredit
        if metode_pembayaran == "KREDIT" and not nama_pelanggan.strip():
            message = '<div class="message error">X Nama pelanggan wajib diisi untuk penjualan kredit!</div>'
        else:
            try:
                if supabase:  # ← INDOUT KE DALAM
                    if tipe_harga == '200':
                        harga_beli = HARGA_BELI_1
                    else:
                        harga_beli = HARGA_BELI_2
                    
                    # Hitung total penjualan
                    total_penjualan = jumlah * harga_jual
                    
                    # 🎯 HITUNG HPP (Harga Pokok Penjualan)
                    hpp = jumlah * harga_beli
                    
                    # Cek persediaan tersedia
                    persediaan_result = supabase.table("persediaan_terintegrasi").select("*").eq("id", 1).execute()
                    if not persediaan_result.data:
                        message = '<div class="message error">❌ Persediaan belum diatur! Silakan set persediaan awal terlebih dahulu.</div>'
                    else:
                        persediaan_sekarang = persediaan_result.data[0]['jumlah_persediaan']
                        
                        if jumlah > persediaan_sekarang:
                            message = f'<div class="message error">❌ Stok tidak mencukupi! Stok tersedia: {persediaan_sekarang} ekor</div>'
                        else:
                            # Kurangi persediaan
                            persediaan_baru = persediaan_sekarang - jumlah
                            update_persediaan = supabase.table("persediaan_terintegrasi").update({
                                "jumlah_persediaan": persediaan_baru,
                                "updated_by": user_email,
                                "updated_at": datetime.now().isoformat()
                            }).eq("id", 1).execute()
                            
                            # Simpan transaksi penjualan - TAMBAH FIELD HPP
                            transaksi_data = {
                                "user_id": user_id,
                                "user_email": user_email,
                                "tanggal": tanggal,
                                "nama_barang": nama_barang,
                                "nama_pegawai": nama_pegawai,
                                "jumlah": jumlah,
                                "harga_beli": harga_beli,
                                "harga_jual": harga_jual,
                                "total_penjualan": total_penjualan,
                                "hpp": hpp,  # 🆕 TAMBAH HPP
                                "metode_pembayaran": metode_pembayaran,
                                "nama_pelanggan": nama_pelanggan if metode_pembayaran == "KREDIT" else "",
                                "created_at": datetime.now().isoformat()
                            }
                            
                            insert_result = supabase.table("penjualan").insert(transaksi_data).execute()
                            
                            # ✅ BUAT JURNAL OTOMATIS - ⚠️ BAGIAN INI YANG DIGANTI
                            if insert_result and insert_result.data:
                                transaksi_id = insert_result.data[0]['id']
                                journal_data = {
                                    'tanggal': tanggal,
                                    'nama_barang': nama_barang,
                                    'jumlah': jumlah,
                                    'total_penjualan': total_penjualan,
                                    'hpp': hpp,
                                    'metode_pembayaran': metode_pembayaran,
                                    'nama_pelanggan': nama_pelanggan
                                }
                                
                                # ⚠️ GANTI BAGIAN INI DENGAN KODE BARU:
                                try:
                                    result = create_journal_entries("PENJUALAN", journal_data, user_email)
                                    if result:
                                        logger.info(f"✅ Jurnal penjualan berhasil dibuat untuk transaksi {transaksi_id}")
                                        message = f'<div class="message success">✅ Transaksi berhasil! Jurnal akuntansi dibuat (HPP: {format_currency(hpp)})</div>'
                                    else:
                                        logger.warning(f"⚠️ Gagal membuat jurnal penjualan")
                                        message = f'<div class="message success">✅ Transaksi berhasil! (Catatan: Gagal membuat jurnal)</div>'
                                except Exception as e:
                                    logger.error(f"❌ Error dalam create_journal_entries: {str(e)}")
                                    message = f'<div class="message success">✅ Transaksi berhasil! (Error jurnal: {str(e)})</div>'
                                # ⚠️ END OF REPLACEMENT
                            
                            logger.info(f"✅ Transaksi penjualan oleh {user_email}: {nama_barang} {jumlah} ekor - HPP: {hpp}")
                            
            except Exception as e:
                message = f'<div class="message error">❌ Error menambah transaksi: {str(e)}</div>'
                logger.error(f"❌ Error tambah transaksi penjualan: {str(e)}")
    
    # Handle pelunasan piutang
    if request.method == "POST" and 'bayar_piutang' in request.form:
        penjualan_id = request.form["penjualan_id"]
        jumlah_bayar = int(request.form["jumlah_bayar"])
        tanggal_bayar = request.form["tanggal_bayar"]
        metode_pembayaran = request.form["metode_pembayaran_piutang"]
        
        try:
            if supabase:
                # Cek data penjualan
                penjualan_data = supabase.table("penjualan").select("*").eq("id", penjualan_id).execute()
                if not penjualan_data.data:
                    message = '<div class="message error">❌ Data penjualan tidak ditemukan!</div>'
                else:
                    penjualan = penjualan_data.data[0]
                    
                    # Hitung sisa piutang
                    pelunasan_result = supabase.table("pelunasan_piutang").select("jumlah_bayar").eq("penjualan_id", penjualan_id).execute()
                    total_dibayar = sum([p['jumlah_bayar'] for p in pelunasan_result.data])
                    sisa_piutang = penjualan['total_penjualan'] - total_dibayar
                    
                    if jumlah_bayar > sisa_piutang:
                        message = f'<div class="message error">❌ Jumlah bayar melebihi sisa piutang! Sisa: Rp {sisa_piutang:,}</div>'
                    else:
                        # Simpan data pelunasan
                        pelunasan_data = {
                            "penjualan_id": penjualan_id,
                            "tanggal_bayar": tanggal_bayar,
                            "jumlah_bayar": jumlah_bayar,
                            "metode_pembayaran": metode_pembayaran,
                            "user_email": user_email,
                            "created_at": datetime.now().isoformat()
                        }
                        
                        insert_result = supabase.table("pelunasan_piutang").insert(pelunasan_data).execute()
                        
                        # Buat jurnal untuk penerimaan piutang
                        jurnal_entries = [
                        {
                            "tanggal": tanggal_bayar,
                            "nama_akun": "Kas",
                            "ref": "1110",
                            "debit": jumlah_bayar,
                            "kredit": 0,
                            "deskripsi": f"Pelunasan piutang dari {penjualan.get('nama_pelanggan', '')} - {penjualan['nama_barang']}",
                            "transaksi_type": "PELUNASAN_PIUTANG",
                            "user_email": user_email,  # ✅ GUNAKAN user_email BUKAN created_by
                            "created_at": datetime.now().isoformat()
                        },
                        {
                            "tanggal": tanggal_bayar,
                            "nama_akun": "Piutang Usaha",
                            "ref": "1120",
                            "debit": 0,
                            "kredit": jumlah_bayar,
                            "deskripsi": f"Pelunasan piutang {penjualan.get('nama_pelanggan', '')}",
                            "transaksi_type": "PELUNASAN_PIUTANG",
                            "user_email": user_email,  # ✅ GUNAKAN user_email BUKAN created_by
                            "created_at": datetime.now().isoformat()
                        }
                    ]
                        
                        for entry in jurnal_entries:
                            supabase.table("jurnal_umum").insert(entry).execute()
                        
                        message = f'<div class="message success">✅ Pelunasan piutang berhasil! Jumlah: Rp {jumlah_bayar:,}</div>'
                        logger.info(f"✅ Pelunasan piutang oleh {user_email}: {jumlah_bayar} untuk penjualan {penjualan_id}")
                        
        except Exception as e:
            message = f'<div class="message error">❌ Error proses pelunasan: {str(e)}</div>'
            logger.error(f"❌ Error pelunasan piutang: {str(e)}")
    
    # Ambil data persediaan terintegrasi
    persediaan_sekarang = 0
    try:
        if supabase:
            result = supabase.table("persediaan_terintegrasi").select("*").eq("id", 1).execute()
            if result.data:
                persediaan_sekarang = result.data[0]['jumlah_persediaan']
    except Exception as e:
        logger.error(f"Error ambil persediaan: {str(e)}")
    
    # Ambil data transaksi penjualan dari SEMUA USER
    transaksi_penjualan = []
    total_penjualan_all = 0
    total_ekor_terjual = 0
    
    try:
        if supabase:
            result = supabase.table("penjualan").select("*").order("tanggal", desc=True).execute()
            transaksi_penjualan = result.data
            
            # Hitung totals
            for transaksi in transaksi_penjualan:
                total_penjualan_all += transaksi['total_penjualan']
                total_ekor_terjual += transaksi['jumlah']
                
    except Exception as e:
        logger.error(f"Error ambil transaksi penjualan: {str(e)}")
    
    # Ambil data piutang (penjualan kredit yang belum lunas)
    data_piutang = []
    total_piutang = 0
    try:
        if supabase:
            # Ambil penjualan kredit yang belum memiliki pelunasan lengkap
            result = supabase.table("penjualan").select("*").eq("metode_pembayaran", "KREDIT").execute()
            for penjualan in result.data:
                # Hitung total yang sudah dibayar
                pelunasan_result = supabase.table("pelunasan_piutang").select("jumlah_bayar").eq("penjualan_id", penjualan['id']).execute()
                total_dibayar = sum([p['jumlah_bayar'] for p in pelunasan_result.data])
                sisa_piutang = penjualan['total_penjualan'] - total_dibayar
                
                if sisa_piutang > 0:
                    data_piutang.append({
                        'id': penjualan['id'],
                        'tanggal': penjualan['tanggal'],
                        'nama_pelanggan': penjualan.get('nama_pelanggan', ''),
                        'nama_barang': penjualan['nama_barang'],
                        'total_penjualan': penjualan['total_penjualan'],
                        'total_dibayar': total_dibayar,
                        'sisa_piutang': sisa_piutang,
                        'user_email': penjualan['user_email']
                    })
                    total_piutang += sisa_piutang
    except Exception as e:
        logger.error(f"Error ambil data piutang: {str(e)}")

    # HTML untuk halaman penjualan
    penjualan_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Penjualan - PINKILANG</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: 'Arial Rounded MT Bold', 'Arial', sans-serif;
                background: linear-gradient(135deg, #ffe6f2, #fff0f7);
                min-height: 100vh;
                padding: 20px;
            }}
            
            .container {{
                max-width: 1400px;
                margin: 0 auto;
                background: white;
                border-radius: 20px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                overflow: hidden;
            }}
            
            .header {{
                background: linear-gradient(135deg, #ff85b3, #ff66a3);
                color: white;
                padding: 30px;
                text-align: center;
            }}
            
            .back-btn {{
                display: inline-block;
                padding: 10px 20px;
                background: rgba(255,255,255,0.2);
                color: white;
                text-decoration: none;
                border-radius: 10px;
                margin-bottom: 20px;
                border: 1px solid rgba(255,255,255,0.3);
            }}
            
            .back-btn:hover {{
                background: rgba(255,255,255,0.3);
            }}
            
            h1 {{
                font-size: 36px;
                margin-bottom: 10px;
            }}
            
            .content {{
                padding: 30px;
            }}
            
            .section {{
                margin-bottom: 40px;
                padding: 25px;
                background: #fff5f9;
                border-radius: 15px;
                border-left: 5px solid #ff85b3;
                box-shadow: 0 4px 15px rgba(255,133,179,0.1);
            }}
            
            .section-title {{
                color: #ff66a3;
                font-size: 24px;
                margin-bottom: 20px;
                padding-bottom: 10px;
                border-bottom: 2px solid #ffe6f2;
            }}
            
            .form-grid {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
                margin-bottom: 20px;
            }}
            
            .form-group {{
                margin-bottom: 15px;
            }}
            
            label {{
                display: block;
                margin-bottom: 5px;
                color: #d63384;
                font-weight: bold;
            }}
            
            input, select {{
                width: 100%;
                padding: 12px;
                border: 2px solid #ffd1e6;
                border-radius: 10px;
                font-size: 16px;
                transition: border-color 0.3s ease;
                background: white;
            }}
            
            input:focus, select:focus {{
                border-color: #ff66a3;
                outline: none;
                box-shadow: 0 0 0 3px rgba(255,102,163,0.1);
            }}
            
            .btn {{
                padding: 12px 30px;
                background: linear-gradient(135deg, #ff85b3, #ff66a3);
                color: white;
                border: none;
                border-radius: 10px;
                cursor: pointer;
                font-size: 16px;
                transition: all 0.3s ease;
                font-weight: bold;
            }}
            
            .btn:hover {{
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(255,102,163,0.3);
                background: linear-gradient(135deg, #ff66a3, #ff4d94);
            }}
            
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin: 20px 0;
            }}
            
            .stat-card {{
                background: white;
                padding: 20px;
                border-radius: 10px;
                text-align: center;
                box-shadow: 0 4px 15px rgba(255,133,179,0.1);
                border: 1px solid #ffe6f2;
                transition: transform 0.3s ease;
            }}
            
            .stat-card:hover {{
                transform: translateY(-5px);
            }}
            
            .stat-number {{
                font-size: 24px;
                font-weight: bold;
                color: #ff66a3;
                margin: 10px 0;
            }}
            
            .stat-label {{
                color: #e83e8c;
                font-size: 14px;
                font-weight: bold;
            }}
            
            .table-container {{
                overflow-x: auto;
                margin-top: 20px;
            }}
            
            table {{
                width: 100%;
                border-collapse: collapse;
                background: white;
                border-radius: 10px;
                overflow: hidden;
                box-shadow: 0 4px 15px rgba(255,133,179,0.1);
            }}
            
            th, td {{
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid #ffe6f2;
                font-size: 14px;
            }}
            
            th {{
                background: linear-gradient(135deg, #ff85b3, #ff66a3);
                color: white;
                font-weight: bold;
            }}
            
            tr:hover {{
                background: #fff5f9;
            }}
            
            .user-badge {{
                background: #ffb6d9;
                color: #c2185b;
                padding: 4px 8px;
                border-radius: 12px;
                font-size: 12px;
                font-weight: bold;
            }}
            
            .current-user {{
                background: #ff66a3;
                color: white;
            }}
            
            .harga-badge {{
                background: #00cc66;
                color: white;
                padding: 4px 8px;
                border-radius: 8px;
                font-size: 11px;
                font-weight: bold;
            }}
            
            .message {{
                padding: 15px;
                margin: 15px 0;
                border-radius: 10px;
                font-size: 14px;
            }}
            
            .success {{
                background: #d4edda;
                color: #155724;
                border: 1px solid #c3e6cb;
            }}
            
            .error {{
                background: #f8d7da;
                color: #721c24;
                border: 1px solid #f5c6cb;
            }}
            
            .info-box {{
                background: #ffe6f2;
                border: 1px solid #ffb6d9;
                border-radius: 10px;
                padding: 15px;
                margin: 15px 0;
                color: #d63384;
            }}
            
            .stock-indicator {{
                background: linear-gradient(135deg, #ff85b3, #ff66a3);
                color: white;
                padding: 8px 15px;
                border-radius: 20px;
                font-weight: bold;
                display: inline-block;
                margin: 5px 0;
            }}
            
            .payment-badge {{
                background: #66b3ff;
                color: white;
                padding: 4px 8px;
                border-radius: 8px;
                font-size: 11px;
                font-weight: bold;
            }}
            
            .payment-badge.cash {{
                background: #00cc66;
            }}
            
            .payment-badge.kredit {{
                background: #ff6666;
            }}
            
            .piutang-badge {{
                background: #ffb366;
                color: white;
                padding: 4px 8px;
                border-radius: 8px;
                font-size: 11px;
                font-weight: bold;
            }}
            
            .piutang-badge.lunas {{
                background: #00cc66;
            }}
            
            .piutang-badge.belum {{
                background: #ff6666;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <!-- Header -->
            <div class="header">
                <a href="/dashboard" class="back-btn">← Kembali ke Dashboard</a>
                <h1>🛍️ Modul Penjualan</h1>
                <p>Sistem Persediaan Terintegrasi - PINKILANG</p>
                <div style="margin-top: 10px; font-size: 14px; opacity: 0.9;">
                    👋 Login sebagai: <strong>{user_email}</strong>
                </div>
            </div>
            
            <!-- Content -->
            <div class="content">
                {message}
                
                <!-- Persediaan Awal Section -->
                <div class="section">
                    <h2 class="section-title">📦 Kelola Persediaan (Terintegrasi)</h2>
                    <div class="info-box">
                        <strong>ℹ️ Info:</strong> Stok persediaan bersifat terpusat untuk semua user.
                    </div>
                    <form method="POST">
                        <div class="form-group">
                            <label for="persediaan_awal">Jumlah Persediaan (ekor):</label>
                            <input type="number" id="persediaan_awal" name="persediaan_awal" 
                                   value="{persediaan_sekarang}" step="1" min="0" required>
                            <small style="color: #666;">* Stok saat ini: <strong>{persediaan_sekarang} ekor</strong></small>
                        </div>
                        <button type="submit" name="set_persediaan" class="btn">💾 Update Stok Persediaan</button>
                    </form>
                </div>
                
                <!-- Input Transaksi Penjualan Section -->
                <div class="section">
                    <h2 class="section-title">➕ Input Transaksi Penjualan</h2>
                    <form method="POST">
                        <div class="form-grid">
                            <div class="form-group">
                                <label for="tanggal">📅 Tanggal Transaksi:</label>
                                <input type="date" id="tanggal" name="tanggal" 
                                       value="{datetime.now().strftime('%Y-%m-%d')}" required>
                            </div>
                            <div class="form-group">
                                <label for="nama_pegawai">👨‍💼 Nama Pegawai:</label>
                                <input type="text" id="nama_pegawai" name="nama_pegawai" 
                                       placeholder="Nama pegawai yang menangani" required>
                            </div>
                            <div class="form-group">
                                <label for="nama_barang">📦 Nama Barang:</label>
                                <input type="text" id="nama_barang" name="nama_barang" 
                                       placeholder="Nama barang yang dijual" required>
                            </div>
                            <div class="form-group">
                                <label for="jumlah">🔢 Jumlah Barang (ekor):</label>
                                <input type="number" id="jumlah" name="jumlah" 
                                       placeholder="0" step="1" min="1" max="{persediaan_sekarang}" required>
                                <small style="color: #666;">Stok tersedia: {persediaan_sekarang} ekor</small>
                            </div>
                            <div class="form-group">
                                <label for="tipe_harga">💰 Tipe Harga Beli:</label>
                                <select id="tipe_harga" name="tipe_harga" required>
                                    <option value="200">Standard - Rp 200/ekor</option>
                                    <option value="500">Premium - Rp 500/ekor</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label for="harga_jual">💵 Harga Jual per ekor (Rp):</label>
                                <input type="number" id="harga_jual" name="harga_jual" 
                                       placeholder="0" step="1" min="0" required>
                            </div>
                            <div class="form-group">
                                <label for="metode_pembayaran">💳 Metode Pembayaran:</label>
                                <select id="metode_pembayaran" name="metode_pembayaran" required>
                                    <option value="CASH">💰 Cash</option>
                                    <option value="KREDIT">📄 Kredit</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label for="nama_pelanggan">👤 Nama Pelanggan:</label>
                                <input type="text" id="nama_pelanggan" name="nama_pelanggan" 
                                       placeholder="Nama pelanggan (isi jika kredit)">
                                <small style="color: #666;">*Wajib diisi untuk penjualan kredit</small>
                            </div>
                        </div>
                        <button type="submit" name="add_penjualan" class="btn">💰 Proses Penjualan</button>
                    </form>
                </div>
                
                <!-- Ringkasan Penjualan -->
                <div class="section">
                    <h2 class="section-title">📊 Ringkasan Penjualan (Semua User)</h2>
                    <div class="stats-grid">
                        <div class="stat-card">
                            <div>📦</div>
                            <div class="stat-number">{persediaan_sekarang}</div>
                            <div class="stat-label">Stok Tersedia</div>
                        </div>
                        <div class="stat-card">
                            <div>🛍️</div>
                            <div class="stat-number">{total_ekor_terjual}</div>
                            <div class="stat-label">Total Ekor Terjual</div>
                        </div>
                        <div class="stat-card">
                            <div>💰</div>
                            <div class="stat-number">Rp {total_penjualan_all:,.0f}</div>
                            <div class="stat-label">Total Penjualan</div>
                        </div>
                        <div class="stat-card">
                            <div>👥</div>
                            <div class="stat-number">{len(set(t['user_email'] for t in transaksi_penjualan)) if transaksi_penjualan else 0}</div>
                            <div class="stat-label">User Aktif</div>
                        </div>
                    </div>
                </div>
                
                <!-- Daftar Transaksi Penjualan -->
                <div class="section">
                    <h2 class="section-title">📋 Daftar Transaksi Penjualan (Semua User)</h2>
                    <div class="table-container">
                        <table>
                            <thead>
                                <tr>
                                    <th> Tanggal</th>
                                    <th> Input Oleh</th>
                                    <th> Pegawai</th>
                                    <th> Barang</th>
                                    <th> Jumlah</th>
                                    <th> Harga Beli</th>
                                    <th> Harga Jual</th>
                                    <th> Pembayaran</th>
                                    <th> Nama Pelanggan</th>
                                    <th> Total</th>
                                </tr>
                            </thead>
                            <tbody>
                                {''.join([f"""
                                <tr>
                                    <td>{datetime.strptime(t['tanggal'], '%Y-%m-%d').strftime('%d/%m/%Y')}</td>
                                    <td>
                                        <span class="user-badge {'current-user' if t.get('user_email') == user_email else ''}">
                                            {t.get('user_email', 'Unknown')}
                                        </span>
                                    </td>
                                    <td>{t['nama_pegawai']}</td>
                                    <td>{t['nama_barang']}</td>
                                    <td>{t['jumlah']} ekor</td>
                                    <td>
                                        <span class="harga-badge">
                                            Rp {t['harga_beli']}/ekor
                                        </span>
                                    </td>
                                    <td>Rp {t['harga_jual']}/ekor</td>
                                    <td>
                                        <span class="payment-badge {'cash' if t.get('metode_pembayaran') == 'CASH' else 'kredit'}">
                                            {'💰 CASH' if t.get('metode_pembayaran') == 'CASH' else '📄 KREDIT'}
                                        </span>
                                    </td>
                                    <td>{t.get('nama_pelanggan', '-')}</td>
                                    <td><strong>Rp {t['total_penjualan']:,.0f}</strong></td>
                                </tr>
                                """ for t in transaksi_penjualan]) if transaksi_penjualan else '''
                                <tr>
                                    <td colspan="10" style="text-align: center; padding: 40px; color: #ff85b3;">
                                        💝 Belum ada transaksi penjualan
                                    </td>
                                </tr>
                                '''}
                            </tbody>
                        </table>
                    </div>
                </div>
                
                <!-- Pelunasan Piutang Section -->
                <div class="section">
                    <h2 class="section-title">💳 Pelunasan Piutang</h2>
                    
                    <!-- Form Pelunasan Piutang -->
                    <form method="POST">
                        <div class="form-grid">
                            <div class="form-group">
                                <label for="penjualan_id">📋 Pilih Penjualan Kredit:</label>
                                <select id="penjualan_id" name="penjualan_id" required>
                                    <option value="">Pilih Penjualan Kredit</option>
                                    {"".join([f"""
                                    <option value="{piutang['id']}" data-sisa="{piutang['sisa_piutang']}">
                                        {piutang['nama_pelanggan']} - {piutang['nama_barang']} (Sisa: Rp {piutang['sisa_piutang']:,})
                                    </option>
                                    """ for piutang in data_piutang])}
                                </select>
                            </div>
                            <div class="form-group">
                                <label for="jumlah_bayar">💰 Jumlah Bayar (Rp):</label>
                                <input type="number" id="jumlah_bayar" name="jumlah_bayar" 
                                       placeholder="0" step="1" min="1" required>
                            </div>
                            <div class="form-group">
                                <label for="tanggal_bayar">📅 Tanggal Bayar:</label>
                                <input type="date" id="tanggal_bayar" name="tanggal_bayar" 
                                       value="{datetime.now().strftime('%Y-%m-%d')}" required>
                            </div>
                            <div class="form-group">
                                <label for="metode_pembayaran_piutang">💳 Metode Pembayaran:</label>
                                <select id="metode_pembayaran_piutang" name="metode_pembayaran_piutang" required>
                                    <option value="CASH">💰 Cash</option>
                                    <option value="TRANSFER">🏦 Transfer</option>
                                    <option value="QRIS">📱 QRIS</option>
                                </select>
                            </div>
                        </div>
                        <button type="submit" name="bayar_piutang" class="btn">💳 Proses Pelunasan</button>
                    </form>
                    
                    <!-- Ringkasan Piutang -->
                    <div style="margin-top: 30px;">
                        <h3 style="color: #ff66a3; margin-bottom: 15px;">📊 Ringkasan Piutang</h3>
                        <div class="stats-grid">
                            <div class="stat-card">
                                <div>📋</div>
                                <div class="stat-number">{len(data_piutang)}</div>
                                <div class="stat-label">Total Piutang</div>
                            </div>
                            <div class="stat-card">
                                <div>💰</div>
                                <div class="stat-number">Rp {total_piutang:,}</div>
                                <div class="stat-label">Total Belum Lunas</div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Daftar Piutang -->
                    <div style="margin-top: 20px;">
                        <h3 style="color: #ff66a3; margin-bottom: 15px;">📋 Daftar Piutang</h3>
                        <div class="table-container">
                            <table>
                                <thead>
                                    <tr>
                                        <th>Tanggal</th>
                                        <th>Pelanggan</th>
                                        <th>Barang</th>
                                        <th>Total Penjualan</th>
                                        <th>Terbayar</th>
                                        <th>Sisa</th>
                                        <th>Status</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {"".join([f"""
                                    <tr>
                                        <td>{datetime.strptime(p['tanggal'], '%Y-%m-%d').strftime('%d/%m/%Y')}</td>
                                        <td><strong>{p['nama_pelanggan']}</strong></td>
                                        <td>{p['nama_barang']}</td>
                                        <td>Rp {p['total_penjualan']:,}</td>
                                        <td>Rp {p['total_dibayar']:,}</td>
                                        <td>Rp {p['sisa_piutang']:,}</td>
                                        <td>
                                            <span class="piutang-badge {'lunas' if p['sisa_piutang'] == 0 else 'belum'}">
                                                {'✅ LUNAS' if p['sisa_piutang'] == 0 else '⏳ BELUM LUNAS'}
                                            </span>
                                        </td>
                                    </tr>
                                    """ for p in data_piutang]) if data_piutang else '''
                                    <tr>
                                        <td colspan="7" style="text-align: center; padding: 20px; color: #ff85b3;">
                                            💝 Tidak ada piutang yang belum lunas
                                        </td>
                                    </tr>
                                    '''}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return penjualan_html

# ============================================================
# 🔹 ROUTE: Pembelian 
# ============================================================
@app.route("/pembelian", methods=["GET", "POST"])
def pembelian():
    if not session.get('logged_in'):
        return redirect('/login')

    user_id = session.get('user_id')
    user_email = session.get('user_email')
    message = ""

    # Harga pembelian tetap per ekor
    HARGA_BELI_1 = 200  # Rp 200 per ekor
    HARGA_BELI_2 = 500  # Rp 500 per ekor

    # ---- helpers lokal ----
    def to_int(x):
        try:
            return int(x)
        except Exception:
            return 0

    def rp(v):
        try:
            return f"Rp {int(v):,}".replace(",", ".")
        except Exception:
            return "Rp 0"

    # --------------------------------------------------------
    # POST: Tambah pembelian
    # --------------------------------------------------------
    if request.method == "POST" and 'add_pembelian' in request.form:
        tanggal = request.form.get("tanggal")
        nama_barang = request.form.get("nama_barang", "").strip()
        nama_supplier = request.form.get("nama_supplier", "").strip()
        jumlah = to_int(request.form.get("jumlah"))
        tipe_harga = request.form.get("tipe_harga")
        metode_pembayaran = request.form.get("metode_pembayaran", "CASH").upper()

        # Validasi dasar
        if jumlah <= 0:
            message = '<div class="message error">❌ Jumlah harus lebih dari 0.</div>'
        elif not nama_barang or not nama_supplier:
            message = '<div class="message error">❌ Nama barang & supplier wajib diisi.</div>'
        else:
            try:
                # pilih harga beli
                harga_beli_per_ekor = HARGA_BELI_1 if tipe_harga == '200' else HARGA_BELI_2
                total_pembelian = jumlah * harga_beli_per_ekor

                # ambil persediaan
                pers_res = supabase.table("persediaan_terintegrasi").select("*").eq("id", 1).execute()
                if not (pers_res and getattr(pers_res, "data", None)):
                    # buat record persediaan awal
                    now_iso = datetime.now().isoformat()
                    supabase.table("persediaan_terintegrasi").insert({
                        "id": 1,
                        "jumlah_persediaan": jumlah,
                        "created_by": user_email,
                        "updated_by": user_email,
                        "created_at": now_iso,
                        "updated_at": now_iso
                    }).execute()
                    persediaan_baru = jumlah
                else:
                    persediaan_sekarang = pers_res.data[0].get("jumlah_persediaan", 0)
                    persediaan_baru = int(persediaan_sekarang) + jumlah
                    supabase.table("persediaan_terintegrasi").update({
                        "jumlah_persediaan": persediaan_baru,
                        "updated_by": user_email,
                        "updated_at": datetime.now().isoformat()
                    }).eq("id", 1).execute()

                # simpan pembelian
                transaksi_data = {
                    "user_id": user_id,
                    "user_email": user_email,
                    "tanggal": tanggal,
                    "nama_barang": nama_barang,
                    "nama_supplier": nama_supplier,
                    "jumlah": jumlah,
                    "harga_beli_per_ekor": harga_beli_per_ekor,
                    "total_pembelian": total_pembelian,
                    "metode_pembayaran": metode_pembayaran,
                    "created_at": datetime.now().isoformat()
                }
                ins = supabase.table("pembelian").insert(transaksi_data).execute()
                if not (ins and getattr(ins, "data", None)):
                    message = '<div class="message error">❌ Gagal menyimpan pembelian (DB).</div>'
                    logger.error("Insert pembelian gagal: %s", getattr(ins, "error", "no-detail"))
                else:
                    pembelian_id = ins.data[0]['id']

                    # jika kredit -> juga masukkan record utang (supaya mudah dilunasi)
                    if metode_pembayaran == "KREDIT":
                        try:
                            # utang: kredit sisi Pembelian
                            utang_payload = {
                                "user_id": user_id,
                                "user_email": user_email,
                                "tanggal": tanggal,
                                "keterangan": f"Pembelian kredit {nama_barang} dari {nama_supplier}",
                                "akun_lawan": "Pembelian",
                                "debit": 0,
                                "kredit": total_pembelian,
                                "jenis": "pembelian_kredit",
                                "ref_id": pembelian_id,
                                "created_at": datetime.now().isoformat()
                            }
                            supabase.table("utang").insert(utang_payload).execute()
                        except Exception as e:
                            logger.warning("Gagal insert utang record: %s", str(e))

                    # Buat jurnal otomatis (Pembelian & Persediaan/HPP)
                    try:
                        if metode_pembayaran == "KREDIT":
                            # Persediaan debit
                            supabase.table("jurnal_umum").insert({
                                "tanggal": tanggal,
                                "nama_akun": "Persediaan",
                                "deskripsi": f"Pembelian (persediaan) {nama_barang}",
                                "debit": total_pembelian,
                                "kredit": 0,
                                "user_email": user_email,
                                "created_at": datetime.now().isoformat()
                            }).execute()
                            # Utang kredit
                            supabase.table("jurnal_umum").insert({
                                "tanggal": tanggal,
                                "nama_akun": "Utang Usaha",
                                "deskripsi": f"Pembelian kredit dari {nama_supplier}",
                                "debit": 0,
                                "kredit": total_pembelian,
                                "user_email": user_email,
                                "created_at": datetime.now().isoformat()
                            }).execute()
                        else:
                            # CASH: Persediaan debit
                            supabase.table("jurnal_umum").insert({
                                "tanggal": tanggal,
                                "nama_akun": "Persediaan",
                                "deskripsi": f"Pembelian (persediaan) {nama_barang}",
                                "debit": total_pembelian,
                                "kredit": 0,
                                "user_email": user_email,
                                "created_at": datetime.now().isoformat()
                            }).execute()
                            # Kas kredit
                            supabase.table("jurnal_umum").insert({
                                "tanggal": tanggal,
                                "nama_akun": "Kas",
                                "deskripsi": f"Pembayaran pembelian tunai ke {nama_supplier}",
                                "debit": 0,
                                "kredit": total_pembelian,
                                "user_email": user_email,
                                "created_at": datetime.now().isoformat()
                            }).execute()

                        logger.info("Jurnal pembelian dibuat untuk transaksi %s", pembelian_id)
                    except Exception as je:
                        logger.error("Gagal membuat jurnal pembelian: %s", str(je))

                    message = f'<div class="message success">✅ Pembelian berhasil! Stok bertambah {jumlah} ekor</div>'

            except Exception as e:
                message = f'<div class="message error">❌ Error menambah pembelian: {str(e)}</div>'
                logger.error("Error tambah pembelian: %s", str(e))

    # --------------------------------------------------------
    # POST: Pelunasan utang 
    # --------------------------------------------------------
    if request.method == "POST" and 'bayar_utang' in request.form:
        pembelian_id = request.form.get("pembelian_id")
        tanggal_bayar = request.form.get("tanggal_bayar")
        jumlah_bayar = to_int(request.form.get("jumlah_bayar"))
        metode_bayar = request.form.get("metode_pembayaran_utang", "CASH").upper()

        try:
            # ambil pembelian untuk cek sisa utang
            pen_res = supabase.table("pembelian").select("*").eq("id", pembelian_id).execute()
            if not (pen_res and getattr(pen_res, "data", None) and len(pen_res.data) > 0):
                message = '<div class="message error">❌ Pembelian tidak ditemukan.</div>'
            else:
                pemb = pen_res.data[0]
                if pemb.get("metode_pembayaran", "").upper() != "KREDIT":
                    message = '<div class="message error">❌ Transaksi pembelian ini bukan kredit / tidak punya utang.</div>'
                else:
                    total_pembelian = int(pemb.get("total_pembelian", 0))
                    # hitung total pelunasan yang sudah ada
                    pel_res = supabase.table("pelunasan_utang").select("jumlah_bayar").eq("pembelian_id", pembelian_id).execute()
                    already_paid = sum([p.get("jumlah_bayar", 0) for p in (pel_res.data or [])])
                    sisa = total_pembelian - already_paid

                    if jumlah_bayar <= 0:
                        message = '<div class="message error">❌ Jumlah bayar harus > 0.</div>'
                    elif jumlah_bayar > sisa:
                        message = f'<div class="message error">❌ Jumlah bayar melebihi sisa ({rp(sisa)}).</div>'
                    else:
                        # ambil nama supplier dari pembelian
                        nama_supplier = pemb.get("nama_supplier", "")

                        # simpan pelunasan_utang
                        pelunasan_payload = {
                            "pembelian_id": pembelian_id,
                            "tanggal_bayar": tanggal_bayar,
                            "jumlah_bayar": jumlah_bayar,
                            "metode_pembayaran": metode_bayar,
                            "user_email": user_email,
                            "nama_supplier": nama_supplier,  
                            "created_at": datetime.now().isoformat()
                        }

                        ins_p = supabase.table("pelunasan_utang").insert(pelunasan_payload).execute()
                        if not (ins_p and getattr(ins_p, "data", None)):
                            message = '<div class="message error">❌ Gagal menyimpan pelunasan (DB).</div>'
                            logger.error("Insert pelunasan_utang gagal: %s", getattr(ins_p, "error", "no-detail"))
                        else:
                            # buat jurnal pelunasan: Utang (D) / Kas/Bank (K)
                            akun_kredit = "Kas" if metode_bayar == "CASH" else "Bank"
                            try:
                                supabase.table("jurnal_umum").insert({
                                    "tanggal": tanggal_bayar,
                                    "nama_akun": "Utang Usaha",
                                    "deskripsi": f"Pelunasan utang pembelian supplier {nama_supplier}",
                                    "debit": jumlah_bayar,
                                    "kredit": 0,
                                    "user_email": user_email,
                                    "created_at": datetime.now().isoformat()
                                }).execute()
                                supabase.table("jurnal_umum").insert({
                                    "tanggal": tanggal_bayar,
                                    "nama_akun": akun_kredit,
                                    "deskripsi": f"Pembayaran pelunasan utang pembelian ID {pembelian_id}",
                                    "debit": 0,
                                    "kredit": jumlah_bayar,
                                    "user_email": user_email,
                                    "created_at": datetime.now().isoformat()
                                }).execute()
                            except Exception as je:
                                logger.error("Gagal membuat jurnal pelunasan utang: %s", str(je))

                            message = f'<div class="message success">✅ Pelunasan utang berhasil: {rp(jumlah_bayar)}</div>'
                            logger.info("Pelunasan utang: pembelian %s dibayar %s oleh %s", pembelian_id, jumlah_bayar, user_email)

        except Exception as e:
            message = f'<div class="message error">❌ Error proses pelunasan: {str(e)}</div>'
            logger.error("Error pelunasan utang: %s", str(e))

    # --------------------------------------------------------
    # Ambil data untuk tampilan: persediaan, pembelian, utang (kredit)
    # --------------------------------------------------------
    persediaan_sekarang = 0
    try:
        pres = supabase.table("persediaan_terintegrasi").select("*").eq("id", 1).execute()
        if pres and pres.data:
            persediaan_sekarang = int(pres.data[0].get("jumlah_persediaan", 0))
    except Exception as e:
        logger.error("Error ambil persediaan: %s", str(e))

    transaksi_pembelian = []
    total_pembelian_all = 0
    total_ekor_dibeli = 0
    try:
        res_all = supabase.table("pembelian").select("*").order("tanggal", desc=True).execute()
        transaksi_pembelian = res_all.data or []
        for t in transaksi_pembelian:
            total_pembelian_all += int(t.get('total_pembelian', 0))
            total_ekor_dibeli += int(t.get('jumlah', 0))
    except Exception as e:
        logger.error("Error ambil pembelian: %s", str(e))

    # ambil daftar pembelian kredit (utang) dan hitung sisa utk tiap entri
    daftar_utang = []
    total_utang = 0
    try:
        kred_res = supabase.table("pembelian").select("*").eq("metode_pembayaran", "KREDIT").execute()
        for pemb in (kred_res.data or []):
            pel_res = supabase.table("pelunasan_utang").select("jumlah_bayar").eq("pembelian_id", pemb['id']).execute()
            sudah_bayar = sum([p.get("jumlah_bayar", 0) for p in (pel_res.data or [])])
            sisa = int(pemb['total_pembelian']) - int(sudah_bayar)

            if sisa > 0:
                # Tambahkan ke daftar utang yang belum lunas
                daftar_utang.append({
                    'id': pemb['id'],
                    'tanggal': pemb['tanggal'],
                    'nama_supplier': pemb.get('nama_supplier', ''),
                    'nama_barang': pemb.get('nama_barang', ''),
                    'total_pembelian': int(pemb.get('total_pembelian', 0)),
                    'sudah_bayar': int(sudah_bayar),
                    'sisa': int(sisa),
                    'user_email': pemb.get('user_email', '')
                })
                total_utang += int(sisa)
    except Exception as e:
        logger.error("Error ambil data utang: %s", str(e))

    # ambil data pelunasan utk tabel riwayat
    data_pelunasan = []
    try:
        pel_all = supabase.table("pelunasan_utang").select("*").order("tanggal_bayar", desc=True).execute()
        data_pelunasan = pel_all.data or []
    except Exception as e:
        logger.error("Error ambil pelunasan utang: %s", str(e))

    
    # --------------------------------------------------------
    # Tampilan Pembelian
    # --------------------------------------------------------
    pembelian_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Pembelian - PINKILANG</title>
        <meta charset="utf-8" />
        <style>
            * {{ margin:0; padding:0; box-sizing:border-box; }}
            body {{ font-family: 'Arial Rounded MT Bold', Arial, sans-serif; background:linear-gradient(135deg,#ffe6f2,#fff0f7); padding:20px; }}
            .container {{ max-width:1400px; margin:0 auto; background:white; border-radius:20px; overflow:hidden; }}
            .header {{ background:linear-gradient(135deg,#ff85b3,#ff66a3); color:white; padding:30px; text-align:center; }}
            .content {{ padding:30px; }}
            .section {{ margin-bottom:30px; padding:20px; background:#fff5f9; border-radius:12px; }}
            .form-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:20px; }}
            input, select {{ width:100%; padding:10px; border-radius:8px; border:2px solid #ffd1e6; }}
            button {{ padding:10px 18px; background:linear-gradient(135deg,#ff85b3,#ff66a3); color:white; border:none; border-radius:8px; cursor:pointer; }}
            table {{ width:100%; border-collapse:collapse; margin-top:10px; }}
            th, td {{ padding:10px; border-bottom:1px solid #f3d6e3; text-align:left; }}
            th {{ background:linear-gradient(135deg,#ff85b3,#ff66a3); color:white; }}
            .message {{ padding:12px; border-radius:8px; margin-bottom:12px; }}
            .success {{ background:#d4edda; color:#155724; }}
            .error {{ background:#f8d7da; color:#721c24; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <a href="/dashboard" style="color:white; text-decoration:none;">← Kembali ke Dashboard</a>
                <h1>🛒 Modul Pembelian</h1>
                <div style="margin-top:8px;">Login sebagai <strong>{user_email}</strong></div>
            </div>

            <div class="content">
                {message}

                <div class="section">
                    <h2>➕ Input Transaksi Pembelian</h2>
                    <form method="POST">
                        <div class="form-grid">
                            <div>
                                <label>Tanggal</label><br>
                                <input type="date" name="tanggal" value="{datetime.now().strftime('%Y-%m-%d')}" required>
                            </div>
                            <div>
                                <label>Nama Supplier</label><br>
                                <input type="text" name="nama_supplier" required>
                            </div>
                            <div>
                                <label>Nama Barang</label><br>
                                <input type="text" name="nama_barang" required>
                            </div>
                            <div>
                                <label>Jumlah (ekor)</label><br>
                                <input type="number" name="jumlah" min="1" value="1" required>
                                <div style="margin-top:6px;">Stok saat ini: <strong>{persediaan_sekarang}</strong></div>
                            </div>
                            <div>
                                <label>Tipe Harga</label><br>
                                <select name="tipe_harga" required>
                                    <option value="200">Standard - Rp 200/ekor</option>
                                    <option value="500">Premium - Rp 500/ekor</option>
                                </select>
                            </div>
                            <div>
                                <label>Metode Pembayaran</label><br>
                                <select name="metode_pembayaran" required>
                                    <option value="CASH">CASH</option>
                                    <option value="KREDIT">KREDIT</option>
                                </select>
                            </div>
                        </div>

                        <div style="margin-top:12px;">
                            <button type="submit" name="add_pembelian">📥 Proses Pembelian</button>
                        </div>
                    </form>
                </div>

                <div class="section">
                    <h2>💳 Pelunasan Utang</h2>

                    <form method="POST">
                        <div class="form-grid">
                            <div>
                                <label>Pilih Pembelian Kredit (Utang)</label><br>
                                <select name="pembelian_id" required>
                                    <option value="">-- Pilih Pembelian Kredit --</option>
                                    {"".join([f"<option value='{u['id']}'> - {u['nama_supplier']} - {rp(u['total_pembelian'])} (Sisa: {rp(u['sisa'])})</option>" for u in daftar_utang])}
                                </select>
                            </div>
                            <div>
                                <label>Tanggal Bayar</label><br>
                                <input type="date" name="tanggal_bayar" value="{datetime.now().strftime('%Y-%m-%d')}" required>
                            </div>
                            <div>
                                <label>Jumlah Bayar (Rp)</label><br>
                                <input type="number" name="jumlah_bayar" min="1" required>
                            </div>
                            <div>
                                <label>Metode Pembayaran</label><br>
                                <select name="metode_pembayaran_utang" required>
                                    <option value="CASH">CASH</option>
                                    <option value="BANK">BANK</option>
                                </select>
                            </div>
                        </div>

                        <div style="margin-top:12px;">
                            <button type="submit" name="bayar_utang">💳 Proses Pelunasan</button>
                        </div>
                    </form>

                    <br>
                    <h3>Riwayat Pelunasan</h3>
                    <table>
                        <thead>
                            <tr><th>Tanggal</th><th>Supplier</th><th>Jumlah</th><th>Metode</th></tr>
                        </thead>
                        <tbody>
                            {"".join([f"<tr><td>{p['tanggal_bayar']}</td><td>{p['nama_supplier']}</td><td>{rp(p['jumlah_bayar'])}</td><td>{p['metode_pembayaran']}</td></tr>" for p in data_pelunasan])}
                        </tbody>
                    </table>
                </div>

                <div class="section">
                    <h2>📋 Daftar Pembelian</h2>
                    <table>
                        <thead>
                            <tr>
                                <th>Tanggal</th><th>Supplier</th><th>Barang</th><th>Jumlah</th><th>Harga/ekor</th><th>Pembayaran</th><th>Total</th>
                            </tr>
                        </thead>
                        <tbody>
                            {"".join([f"<tr><td>{datetime.strptime(t['tanggal'],'%Y-%m-%d').strftime('%d/%m/%Y')}</td><td>{t['nama_supplier']}</td><td>{t['nama_barang']}</td><td>+{t['jumlah']}</td><td>Rp {t['harga_beli_per_ekor']}</td><td>{t['metode_pembayaran']}</td><td>{rp(t['total_pembelian'])}</td></tr>" for t in transaksi_pembelian])}
                        </tbody>
                    </table>
                </div>

                <div style="padding:20px;">
                    <strong>Total Utang (Belum Lunas):</strong> {rp(total_utang)}
                </div>

            </div>
        </div>
    </body>
    </html>
    """

    return pembelian_html
    
# ============================================================
# ROUTE: Buku Besar - FIXED VERSION (HANDLE None VALUES)
# ============================================================
@app.route("/buku-besar")
def buku_besar():
    if not session.get('logged_in'):
        return redirect('/login')

    user_email = session.get("user_email")

    # =======================================================
    # LOAD DATA JURNAL DARI SUPABASE
    # =======================================================
    try:
        try:
            res = supabase.table("jurnal_umum").select("*").order("tanggal", asc=True).execute()
        except:
            res = supabase.table("jurnal_umum").select("*").order("tanggal", desc=False).execute()

        jurnal_data = res.data or []
    except Exception as e:
        logger.error(f"Error mengambil jurnal: {e}")
        jurnal_data = []

    # =======================================================
    # DEBUG: CEK DATA YANG ADA DENGAN HANDLE None
    # =======================================================
    print("=== DEBUG JURNAL DATA ===")
    for i, row in enumerate(jurnal_data[:10]):  # Print 10 data pertama
        deskripsi = row.get('deskripsi') or row.get('keterangan') or 'No Description'
        print(f"Data {i}: {row.get('nama_akun')} | Debit: {row.get('debit')} | Kredit: {row.get('kredit')} | Deskripsi: {deskripsi}")

    # =======================================================
    # HELPER: FORMAT RUPIAH
    # =======================================================
    def rp(v):
        try:
            if Decimal(str(v)) == 0:
                return "Rp 0"
            return f"Rp {int(v):,}".replace(",", ".")
        except:
            return "Rp 0"

    # =======================================================
    # HELPER FUNCTION: GENERATE SECTION PER AKUN
    # =======================================================
    def generate_akun_section(akun, entries):
        # Sort entries by tanggal
        def safe_date(d):
            t = d.get("tanggal")
            if not t:
                return datetime(1970,1,1)
            try:
                return datetime.fromisoformat(t)
            except:
                try:
                    return datetime.strptime(t, "%Y-%m-%d")
                except:
                    return datetime(1970,1,1)

        entries_sorted = sorted(entries, key=safe_date)

        saldo = Decimal("0")
        rows_html = ""

        for e in entries_sorted:
            # Handle debit kredit dengan safe conversion
            try: 
                debit = Decimal(str(e.get("debit") or 0))
            except: 
                debit = Decimal("0")

            try: 
                kredit = Decimal(str(e.get("kredit") or 0))
            except: 
                kredit = Decimal("0")

            # Hitung saldo berdasarkan jenis akun
            if akun in ["Kas (1110)", "Piutang Usaha (1130)", "Persediaan Barang Dagang (1140)", 
                       "Perlengkapan (1150)", "Tanah (1210)", "Bangunan (1220)", 
                       "Kendaraan (1230)", "Peralatan (1240)"]:
                # Asset: Debit meningkatkan saldo
                saldo = saldo + debit - kredit
            elif akun in ["Akumulasi Penyusutan Bangunan (1221)", "Akumulasi Penyusutan Kendaraan (1231)", 
                         "Akumulasi Penyusutan Peralatan (1241)", "Utang (2100)", 
                         "Pendapatan Diterima Dimuka (2200)", "Modal (3100)", 
                         "Ikhtisar L/R (3300)", "Penjualan (4100)"]:
                # Contra Asset, Liability, Equity & Revenue: Kredit meningkatkan saldo  
                saldo = saldo + kredit - debit
            elif akun in ["Prive Mas Angga (3200)", "Retur Penjualan (4200)", "Potongan Penjualan (4300)",
                         "Pembelian (5200)", "HPP (5110)", "Beban Perlengkapan (6100)",
                         "Beban air, listrik dan telepon (6200)", "Beban Penyusutan (6300)",
                         "Beban Gaji", "Beban Sewa", "Beban Transportasi", "Beban Lain-lain"]:
                # Expense & Drawing: Debit meningkatkan saldo
                saldo = saldo + debit - kredit
            else:
                # Default
                saldo = saldo + debit - kredit

            # Format tanggal
            try:
                tgl = safe_date(e).strftime("%d/%m/%Y")
            except:
                tgl = "-"

            deskripsi = e.get("deskripsi") or e.get("keterangan") or "-"

            rows_html += f"""
                <tr>
                    <td>{tgl}</td>
                    <td>{deskripsi}</td>
                    <td class="debit">{rp(debit)}</td>
                    <td class="kredit">{rp(kredit)}</td>
                    <td class="saldo">{rp(saldo)}</td>
                </tr>
            """

        # Jika tidak ada transaksi, buat baris kosong
        if not entries_sorted:
            rows_html = """
                <tr>
                    <td colspan="5" style="text-align: center; color: #999; padding: 20px;">
                        Belum ada transaksi
                    </td>
                </tr>
            """

        # Tentukan class warna berdasarkan jenis akun
        account_class = ""
        if akun in ["Kas (1110)", "Piutang Usaha (1130)", "Persediaan Barang Dagang (1140)", 
                   "Perlengkapan (1150)", "Tanah (1210)", "Bangunan (1220)", 
                   "Kendaraan (1230)", "Peralatan (1240)"]:
            account_class = "asset-account"
        elif akun in ["Akumulasi Penyusutan Bangunan (1221)", "Akumulasi Penyusutan Kendaraan (1231)", 
                     "Akumulasi Penyusutan Peralatan (1241)"]:
            account_class = "contra-asset-account"
        elif akun in ["Utang (2100)", "Pendapatan Diterima Dimuka (2200)"]:
            account_class = "liability-account"  
        elif akun in ["Modal (3100)", "Prive Mas Angga (3200)", "Ikhtisar L/R (3300)"]:
            account_class = "equity-account"
        elif akun in ["Penjualan (4100)"]:
            account_class = "revenue-account"
        elif akun in ["Retur Penjualan (4200)", "Potongan Penjualan (4300)"]:
            account_class = "contra-revenue-account"
        elif akun in ["Pembelian (5200)", "HPP (5110)"]:
            account_class = "cogs-account"
        elif akun in ["Beban Perlengkapan (6100)", "Beban air, listrik dan telepon (6200)", 
                     "Beban Penyusutan (6300)", "Beban Gaji", "Beban Sewa", 
                     "Beban Transportasi", "Beban Lain-lain"]:
            account_class = "expense-account"
        else:
            account_class = "other-account"

        return f"""
            <div class="akun-block {account_class}">
                <h2 class="akun-title">{akun}</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Tanggal</th>
                            <th>Deskripsi</th>
                            <th>Debit</th>
                            <th>Kredit</th>
                            <th>Saldo</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows_html}
                    </tbody>
                </table>
            </div>
            """

    # =======================================================
    # MAPPING AKUN YANG LEBIH AKURAT - DENGAN HANDLE None
    # =======================================================
    def standardize_account_name(raw_name):
        if not raw_name:
            return "Lainnya"
        
        raw_name = str(raw_name or "").strip().lower()
        
        # ASET LANCAR (1100)
        if any(word in raw_name for word in ['kas', 'tunai', 'bank']):
            return "Kas (1110)"
        elif any(word in raw_name for word in ['piutang', 'receivable']):
            return "Piutang Usaha (1130)"
        elif any(word in raw_name for word in ['persediaan', 'inventory', 'stok', 'barang dagang']):
            return "Persediaan Barang Dagang (1140)"
        elif any(word in raw_name for word in ['perlengkapan', 'supplies']):
            return "Perlengkapan (1150)"
        
        # ASET TETAP (1200)
        elif any(word in raw_name for word in ['tanah']):
            return "Tanah (1210)"
        elif any(word in raw_name for word in ['bangunan', 'gedung']):
            return "Bangunan (1220)"
        elif any(word in raw_name for word in ['akumulasi penyusutan bangunan']):
            return "Akumulasi Penyusutan Bangunan (1221)"
        elif any(word in raw_name for word in ['kendaraan', 'mobil', 'motor']):
            return "Kendaraan (1230)"
        elif any(word in raw_name for word in ['akumulasi penyusutan kendaraan']):
            return "Akumulasi Penyusutan Kendaraan (1231)"
        elif any(word in raw_name for word in ['peralatan', 'equipment']):
            return "Peralatan (1240)"
        elif any(word in raw_name for word in ['akumulasi penyusutan peralatan']):
            return "Akumulasi Penyusutan Peralatan (1241)"
        
        # UTANG (2000)
        elif any(word in raw_name for word in ['utang', 'hutang', 'payable', 'kewajiban']):
            return "Utang (2100)"
        elif any(word in raw_name for word in ['pendapatan diterima dimuka', 'pendapatan dimuka', 'uang muka']):
            return "Pendapatan Diterima Dimuka (2200)"
        
        # MODAL (3000)
        elif any(word in raw_name for word in ['modal', 'equity', 'capital']):
            return "Modal (3100)"
        elif any(word in raw_name for word in ['prive', 'drawing']):
            return "Prive Mas Angga (3200)"
        elif any(word in raw_name for word in ['ikhtisar', 'laba rugi']):
            return "Ikhtisar L/R (3300)"
        
        # PENDAPATAN (4000)
        elif any(word in raw_name for word in ['penjualan', 'sales']):
            return "Penjualan (4100)"
        elif any(word in raw_name for word in ['retur penjualan', 'sales return']):
            return "Retur Penjualan (4200)"
        elif any(word in raw_name for word in ['potongan penjualan', 'sales discount']):
            return "Potongan Penjualan (4300)"
        
        # HPP & PEMBELIAN (5000)
        elif any(word in raw_name for word in ['hpp', 'harga pokok penjualan', 'biaya pokok']):
            return "HPP (5110)"
        elif any(word in raw_name for word in ['pembelian', 'purchase', 'beli']):
            return "Pembelian (5200)"
        
        # BEBAN (6000)
        elif any(word in raw_name for word in ['beban perlengkapan']):
            return "Beban Perlengkapan (6100)"
        elif any(word in raw_name for word in ['beban listrik', 'beban air', 'beban telepon', 'listrik', 'air', 'telepon']):
            return "Beban air, listrik dan telepon (6200)"
        elif any(word in raw_name for word in ['beban penyusutan', 'penyusutan']):
            return "Beban Penyusutan (6300)"
        elif any(word in raw_name for word in ['beban gaji', 'gaji']):
            return "Beban Gaji"
        elif any(word in raw_name for word in ['beban sewa', 'sewa']):
            return "Beban Sewa"
        elif any(word in raw_name for word in ['beban transportasi', 'transport']):
            return "Beban Transportasi"
        elif any(word in raw_name for word in ['beban lain', 'biaya lain']):
            return "Beban Lain-lain"
        
        # Default grouping
        else:
            return "Lainnya"

    # =======================================================
    # KELOMPOK SEMUA AKUN OTOMATIS - DENGAN HANDLE None
    # =======================================================
    ledger = {}

    for row in jurnal_data:
        # Priority 1: Gunakan nama_akun jika ada
        raw_account = row.get("nama_akun") or "UNKNOWN"
        
        # Priority 2: Jika nama_akun tidak ada, tentukan dari pola transaksi
        if raw_account == "UNKNOWN":
            deskripsi = (row.get("deskripsi") or row.get("keterangan") or "").lower()
            transaksi_type = row.get("transaksi_type", "")
            debit = Decimal(str(row.get("debit") or 0))
            kredit = Decimal(str(row.get("kredit") or 0))
            
            # LOGIC UNTUK PEMBELIAN & UTANG
            if any(word in deskripsi for word in ['pembelian', 'beli barang', 'purchase']):
                if debit > 0:
                    raw_account = "Pembelian"  # Pembelian tunai
                elif kredit > 0:
                    raw_account = "Utang"  # Pembelian kredit
                    
            # LOGIC UNTUK MODAL AWAL
            elif any(word in deskripsi for word in ['modal awal', 'tambahan modal', 'setoran modal']):
                raw_account = "Modal"
                
            # LOGIC UNTUK ASET TETAP
            elif any(word in deskripsi for word in ['tanah', 'bangunan', 'kendaraan', 'peralatan']):
                if debit > 0:
                    raw_account = deskripsi  # Langsung gunakan deskripsi
                    
            # LOGIC UNTUK OPERASIONAL
            elif any(word in deskripsi for word in ['listrik', 'air', 'telepon']):
                raw_account = "Beban air, listrik dan telepon"
                
            # Fallback berdasarkan transaksi_type
            elif transaksi_type == "PEMBELIAN":
                raw_account = "Pembelian"
            elif transaksi_type == "TAMBAHAN_MODAL":
                raw_account = "Modal"
            elif transaksi_type == "ASET_TETAP":
                # Coba deteksi jenis aset dari deskripsi
                if any(word in deskripsi for word in ['kendaraan']):
                    raw_account = "Kendaraan"
                elif any(word in deskripsi for word in ['bangunan']):
                    raw_account = "Bangunan"
                elif any(word in deskripsi for word in ['tanah']):
                    raw_account = "Tanah"
                elif any(word in deskripsi for word in ['peralatan']):
                    raw_account = "Peralatan"
        
        # Standardisasi nama akun
        standardized_account = standardize_account_name(raw_account)
        
        print(f"DEBUG MAPPING: '{raw_account}' -> '{standardized_account}' | Deskripsi: {row.get('deskripsi')}")
        
        # Kelompokkan ke ledger
        if standardized_account not in ledger:
            ledger[standardized_account] = []
        ledger[standardized_account].append(row)

    # =======================================================
    # URUTAN AKUN YANG FIXED
    # =======================================================
    account_order = [
        # ASET LANCAR (1100)
        "Kas (1110)",
        "Piutang Usaha (1130)", 
        "Persediaan Barang Dagang (1140)",
        "Perlengkapan (1150)",
        
        # ASET TETAP (1200)
        "Tanah (1210)",
        "Bangunan (1220)",
        "Akumulasi Penyusutan Bangunan (1221)",
        "Kendaraan (1230)",
        "Akumulasi Penyusutan Kendaraan (1231)",
        "Peralatan (1240)",
        "Akumulasi Penyusutan Peralatan (1241)",
        
        # UTANG (2000)
        "Utang (2100)",
        "Pendapatan Diterima Dimuka (2200)",
        
        # MODAL (3000)
        "Modal (3100)",
        "Prive Mas Angga (3200)",
        "Ikhtisar L/R (3300)",
        
        # PENDAPATAN (4000)
        "Penjualan (4100)",
        "Retur Penjualan (4200)",
        "Potongan Penjualan (4300)",
        
        # HPP & PEMBELIAN (5000)
        "Pembelian (5200)",
        "HPP (5110)",
        
        # BEBAN (6000)
        "Beban Perlengkapan (6100)",
        "Beban air, listrik dan telepon (6200)",
        "Beban Penyusutan (6300)",
        "Beban Gaji",
        "Beban Sewa", 
        "Beban Transportasi",
        "Beban Lain-lain",
        "Lainnya"
    ]

    # =======================================================
    # GENERATE SEMUA AKUN
    # =======================================================
    akun_sections = ""

    # ASET LANCAR (1100)
    akun_sections += '<div class="account-category">ASET LANCAR (1100)</div>'
    for akun in account_order[0:4]:
        entries = ledger.get(akun, [])
        section = generate_akun_section(akun, entries)
        akun_sections += section

    # ASET TETAP (1200)
    akun_sections += '<div class="account-category">ASET TETAP (1200)</div>'
    for akun in account_order[4:11]:
        entries = ledger.get(akun, [])
        section = generate_akun_section(akun, entries)
        akun_sections += section

    # UTANG (2000)
    akun_sections += '<div class="account-category">UTANG (2000)</div>'
    for akun in account_order[11:13]:
        entries = ledger.get(akun, [])
        section = generate_akun_section(akun, entries)
        akun_sections += section

    # MODAL (3000)
    akun_sections += '<div class="account-category">MODAL (3000)</div>'
    for akun in account_order[13:16]:
        entries = ledger.get(akun, [])
        section = generate_akun_section(akun, entries)
        akun_sections += section

    # PENDAPATAN (4000)
    akun_sections += '<div class="account-category">PENDAPATAN (4000)</div>'
    for akun in account_order[16:19]:
        entries = ledger.get(akun, [])
        section = generate_akun_section(akun, entries)
        akun_sections += section

    # HPP & PEMBELIAN (5000)
    akun_sections += '<div class="account-category">HPP & PEMBELIAN (5000)</div>'
    for akun in account_order[19:21]:
        entries = ledger.get(akun, [])
        section = generate_akun_section(akun, entries)
        akun_sections += section

    # BEBAN (6000)
    akun_sections += '<div class="account-category">BEBAN (6000)</div>'
    for akun in account_order[21:]:
        entries = ledger.get(akun, [])
        section = generate_akun_section(akun, entries)
        akun_sections += section

    # =======================================================
    # RENDER TAMPILAN BUKU BESAR - FIXED None HANDLING
    # =======================================================
    # Helper untuk debug info yang aman
    def safe_debug_info():
        if not jurnal_data:
            return 'Tidak ada data'
        
        debug_items = []
        for row in jurnal_data[:3]:
            deskripsi = row.get('deskripsi') or row.get('keterangan') or 'No Description'
            # Handle jika deskripsi None atau kosong
            if deskripsi and len(deskripsi) > 30:
                debug_items.append(f"{deskripsi[:30]}...")
            elif deskripsi:
                debug_items.append(deskripsi)
            else:
                debug_items.append("No Description")
        
        return ', '.join(debug_items)

    html = f"""
    <html>
    <head>
        <title>Buku Besar - PINKILANG</title>
        <style>
            /* CSS tetap sama seperti sebelumnya */
            body {{ font-family: Arial, sans-serif; background: #f8f9fa; padding: 20px; margin: 0; }}
            .container {{ background: white; padding: 25px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); max-width: 1200px; margin: 0 auto; }}
            .navigation {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; padding-bottom: 15px; border-bottom: 2px solid #ff6ea9; }}
            .system-title {{ color: #ff6ea9; font-weight: bold; font-size: 18px; }}
            .btn-dashboard {{ background: #ff6ea9; color: white; padding: 10px 20px; text-decoration: none; border-radius: 20px; font-weight: bold; }}
            .header {{ text-align: center; margin-bottom: 30px; }}
            .main-title {{ color: #c4006e; font-size: 28px; margin-bottom: 10px; }}
            .user-info {{ background: #ffeaf4; padding: 10px 20px; border-radius: 20px; color: #c4006e; font-weight: bold; }}
            
            table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
            th, td {{ padding: 12px 15px; border: 1px solid #e0e0e0; text-align: left; }}
            th {{ background: #ff6ea9; color: white; font-weight: bold; }}
            
            .asset-account {{ background: #e8f5e8; border-left: 4px solid #28a745; }}
            .contra-asset-account {{ background: #d4edda; border-left: 4px solid #20c997; }}
            .liability-account {{ background: #fff3cd; border-left: 4px solid #ffc107; }}
            .equity-account {{ background: #d1ecf1; border-left: 4px solid #17a2b8; }}
            .revenue-account {{ background: #e2e3ff; border-left: 4px solid #6f42c1; }}
            .contra-revenue-account {{ background: #e8e2ff; border-left: 4px solid #8b5cf6; }}
            .cogs-account {{ background: #ffeaea; border-left: 4px solid #dc3545; }}
            .expense-account {{ background: #fff0f5; border-left: 4px solid #e83e8c; }}
            
            .akun-block {{ padding: 25px; margin-bottom: 30px; border-radius: 10px; }}
            .akun-title {{ font-size: 20px; margin-bottom: 15px; padding-bottom: 10px; border-bottom: 2px solid; }}
            .asset-account .akun-title {{ color: #28a745; }}
            .contra-asset-account .akun-title {{ color: #20c997; }}
            .liability-account .akun-title {{ color: #ffc107; }}
            .equity-account .akun-title {{ color: #17a2b8; }}
            .revenue-account .akun-title {{ color: #6f42c1; }}
            .contra-revenue-account .akun-title {{ color: #8b5cf6; }}
            .cogs-account .akun-title {{ color: #dc3545; }}
            .expense-account .akun-title {{ color: #e83e8c; }}
            
            .debit {{ color: #008000; font-weight: bold; text-align: right; }}
            .kredit {{ color: #b30000; font-weight: bold; text-align: right; }}
            .saldo {{ font-weight: bold; text-align: right; }}
            .asset-account .saldo {{ color: #28a745; }}
            .contra-asset-account .saldo {{ color: #20c997; }}
            .liability-account .saldo {{ color: #ffc107; }}
            .equity-account .saldo {{ color: #17a2b8; }}
            .revenue-account .saldo {{ color: #6f42c1; }}
            .contra-revenue-account .saldo {{ color: #8b5cf6; }}
            .cogs-account .saldo {{ color: #dc3545; }}
            .expense-account .saldo {{ color: #e83e8c; }}
            
            .footer {{ text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e0e0e0; color: #666; }}
            tr:hover {{ background-color: #f8f9fa; }}
            .debug-info {{ background: #f0f0f0; padding: 10px; border-radius: 5px; margin-bottom: 20px; font-size: 12px; color: #666; }}
            .account-category {{
                background: #c4006e;
                color: white;
                padding: 10px 15px;
                margin: 20px 0 10px 0;
                border-radius: 5px;
                font-weight: bold;
                font-size: 16px;
            }}
        </style>
    </head>

    <body>
        <div class="container">
            <div class="navigation">
                <div class="system-title">Sistem Pencatatan Double Entry - PINKILANG</div>
                <a href="/dashboard" class="btn-dashboard">Kembali ke Dashboard</a>
            </div>

            <div class="header">
                <div class="main-title">Buku Besar</div>
                <div class="subtitle">Laporan detail semua transaksi keuangan</div>
                <div class="user-info">Login sebagai: {user_email}</div>
            </div>

            <div class="debug-info">
                <strong>DEBUG:</strong> {len(jurnal_data)} transaksi ditemukan, {len(ledger)} akun aktif
                <br><strong>Akun yang terdeteksi:</strong> {', '.join(ledger.keys())}
                <br><strong>Contoh data:</strong> {safe_debug_info()}
            </div>

            <!-- Account Sections -->
            {akun_sections}

            <div style="text-align: center; margin-top: 30px;">
                <a href="/dashboard" class="btn-dashboard">Kembali ke Dashboard</a>
            </div>

            <div class="footer">
                <p>Generated by Sistem PINKILANG • {datetime.now().strftime("%d/%m/%Y %H:%M")}</p>
            </div>
        </div>
    </body>
    </html>
    """

    return html
# ============================================================
# ROUTE: Neraca Saldo
# ============================================================
@app.route("/neraca-saldo")
def neraca_saldo():
    # auth check
    try:
        if not session.get("logged_in"):
            return redirect("/login")
    except Exception:
        return "Session not available - ensure `from flask import session` is imported.", 500

    user_email = session.get("user_email", "Unknown")

    # ambil data dari supabase; aman terhadap method order yang berbeda
    try:
        try:
            res = supabase.table("jurnal_umum").select("*").order("tanggal", asc=True).execute()
        except Exception:
            # fallback bila client tidak mengenali asc param
            res = supabase.table("jurnal_umum").select("*").order("tanggal", desc=False).execute()
        jurnal_data = res.data or []
    except NameError:
        return "Supabase client not initialized (variable `supabase` not found).", 500
    except Exception as e:
        # tampilkan pesan singkat di browser agar mudah debug di lingkungan development
        logger.error(f"Error saat load jurnal: {e}")
        return f"Error load jurnal: {str(e)}", 500

    # group per akun dan hitung total debit/kredit
    saldo_akun = {}

    for row in jurnal_data:
        akun = row.get("nama_akun") or "UNKNOWN"

        if akun not in saldo_akun:
            saldo_akun[akun] = {"debit": Decimal("0"), "kredit": Decimal("0")}

        # ambil nilai debit/kredit aman
        raw_d = row.get("debit", 0) or 0
        raw_k = row.get("kredit", 0) or 0

        try:
            d = Decimal(str(raw_d))
        except Exception:
            d = Decimal("0")

        try:
            k = Decimal(str(raw_k))
        except Exception:
            k = Decimal("0")

        saldo_akun[akun]["debit"] += d
        saldo_akun[akun]["kredit"] += k

    # helper format rupiah
    def rp(v):
        try:
            # v bisa Decimal
            return f"Rp {int(v):,}".replace(",", ".")
        except Exception:
            return "Rp 0"

    # generate rows
    rows_html = ""
    total_debit = Decimal("0")
    total_kredit = Decimal("0")

    for akun, val in sorted(saldo_akun.items()):
        d = val["debit"]
        k = val["kredit"]
        total_debit += d
        total_kredit += k

        rows_html += f"""
        <tr>
            <td>{akun}</td>
            <td class="debit">{rp(d)}</td>
            <td class="kredit">{rp(k)}</td>
        </tr>
        """

    # render page
        html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Neraca Saldo - PINKILANG</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #ffe6f2, #ffccde);
                padding: 20px;
                min-height: 100vh;
            }}
            
            .container {{
                max-width: 1000px;
                margin: 0 auto;
                background: white;
                border-radius: 15px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                overflow: hidden;
            }}
            
            .header {{
                background: linear-gradient(135deg, #ff6ea9, #c4006e);
                color: white;
                padding: 25px;
                text-align: center;
                position: relative;
            }}
            
            .back-btn {{
                display: inline-block;
                padding: 10px 20px;
                background: rgba(255,255,255,0.2);
                color: white;
                text-decoration: none;
                border-radius: 8px;
                margin-bottom: 15px;
                border: 1px solid rgba(255,255,255,0.3);
                transition: all 0.3s ease;
                font-weight: 500;
            }}
            
            .back-btn:hover {{
                background: rgba(255,255,255,0.3);
                transform: translateY(-2px);
            }}
            
            h1 {{
                font-size: 28px;
                margin-bottom: 10px;
                font-weight: 600;
            }}
            
            .user-info {{
                font-size: 16px;
                opacity: 0.9;
                margin-top: 5px;
            }}
            
            .content {{
                padding: 30px;
            }}
            
            /* Table Styling */
            .table-container {{
                background: white;
                border-radius: 10px;
                overflow: hidden;
                box-shadow: 0 4px 15px rgba(0,0,0,0.08);
                margin: 20px 0;
            }}
            
            .neraca-table {{
                width: 100%;
                border-collapse: collapse;
                font-size: 14px;
            }}
            
            .neraca-table thead {{
                background: linear-gradient(135deg, #ff6ea9, #c4006e);
            }}
            
            .neraca-table th {{
                padding: 16px 12px;
                text-align: left;
                color: white;
                font-weight: 600;
                font-size: 14px;
                border: none;
            }}
            
            .neraca-table th:first-child {{
                border-radius: 8px 0 0 0;
            }}
            
            .neraca-table th:last-child {{
                border-radius: 0 8px 0 0;
            }}
            
            .neraca-table td {{
                padding: 14px 12px;
                border-bottom: 1px solid #f0f0f0;
                color: #333;
            }}
            
            .neraca-table tbody tr:hover {{
                background: #f8f8f8;
                transform: translateY(-1px);
                transition: all 0.2s ease;
                box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            }}
            
            .neraca-table tfoot {{
                background: #fde3ef;
                font-weight: bold;
            }}
            
            .neraca-table tfoot td {{
                padding: 16px 12px;
                border-bottom: none;
                font-size: 15px;
            }}
            
            .neraca-table tfoot td:first-child {{
                border-radius: 0 0 0 8px;
            }}
            
            .neraca-table tfoot td:last-child {{
                border-radius: 0 0 8px 0;
            }}
            
            /* Color Coding */
            .debit {{
                color: #008000;
                font-weight: 600;
            }}
            
            .kredit {{
                color: #b30000;
                font-weight: 600;
            }}
            
            .akun-name {{
                font-weight: 500;
                color: #333;
            }}
            
            /* Balance Status */
            .balance-status {{
                text-align: center;
                padding: 15px;
                margin: 20px 0;
                border-radius: 10px;
                font-weight: 600;
                font-size: 16px;
            }}
            
            .balance-correct {{
                background: #d4edda;
                color: #155724;
                border: 1px solid #c3e6cb;
            }}
            
            .balance-incorrect {{
                background: #f8d7da;
                color: #721c24;
                border: 1px solid #f5c6cb;
            }}
            
            /* Summary Cards */
            .summary-cards {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin: 25px 0;
            }}
            
            .summary-card {{
                background: #f8f9fa;
                padding: 20px;
                border-radius: 10px;
                text-align: center;
                border-left: 4px solid #ff6ea9;
            }}
            
            .summary-number {{
                font-size: 24px;
                font-weight: bold;
                color: #c4006e;
                margin-bottom: 5px;
            }}
            
            .summary-label {{
                font-size: 14px;
                color: #666;
            }}
            
            /* Action Buttons */
            .action-buttons {{
                text-align: center;
                margin-top: 30px;
                padding-top: 20px;
                border-top: 1px solid #eee;
            }}
            
            .btn {{
                display: inline-block;
                padding: 12px 24px;
                background: #6c757d;
                color: white;
                text-decoration: none;
                border-radius: 6px;
                margin: 0 5px;
                transition: all 0.3s ease;
                font-weight: 500;
                border: none;
                cursor: pointer;
            }}
            
            .btn:hover {{
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            }}
            
            .btn-primary {{
                background: #c4006e;
            }}
            
            .btn-secondary {{
                background: #6c757d;
            }}
            
            .btn-success {{
                background: #28a745;
            }}
            
            /* Responsive */
            @media (max-width: 768px) {{
                .container {{
                    margin: 10px;
                }}
                
                .content {{
                    padding: 20px;
                }}
                
                .neraca-table {{
                    font-size: 12px;
                }}
                
                .neraca-table th,
                .neraca-table td {{
                    padding: 10px 8px;
                }}
                
                .summary-cards {{
                    grid-template-columns: 1fr;
                }}
                
                .action-buttons {{
                    display: flex;
                    flex-direction: column;
                    gap: 10px;
                }}
                
                .btn {{
                    width: 100%;
                    margin: 2px 0;
                }}
            }}
            
            /* Print Styles */
            @media print {{
                body {{
                    background: white;
                    padding: 0;
                }}
                
                .container {{
                    box-shadow: none;
                    margin: 0;
                }}
                
                .back-btn, .action-buttons {{
                    display: none;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <!-- Header -->
            <div class="header">
                <a href="/dashboard" class="back-btn">← Kembali ke Dashboard</a>
                <h1>📊 Neraca Saldo</h1>
                <div class="user-info">Login sebagai: <strong>{user_email}</strong></div>
            </div>
            
            <!-- Content -->
            <div class="content">
                <!-- Summary Cards -->
                <div class="summary-cards">
                    <div class="summary-card">
                        <div class="summary-number">{len(saldo_akun)}</div>
                        <div class="summary-label">Total Akun</div>
                    </div>
                    <div class="summary-card">
                        <div class="summary-number">{rp(total_debit)}</div>
                        <div class="summary-label">Total Debit</div>
                    </div>
                    <div class="summary-card">
                        <div class="summary-number">{rp(total_kredit)}</div>
                        <div class="summary-label">Total Kredit</div>
                    </div>
                </div>
                
                <!-- Balance Status -->
                <div class="balance-status { 'balance-correct' if total_debit == total_kredit else 'balance-incorrect' }">
                    { '✅ NERACA SEIMBANG' if total_debit == total_kredit else '❌ NERACA TIDAK SEIMBANG' }
                    <br>
                    <small>Total Debit: {rp(total_debit)} | Total Kredit: {rp(total_kredit)}</small>
                </div>
                
                <!-- Neraca Table -->
                <div class="table-container">
                    <table class="neraca-table">
                        <thead>
                            <tr>
                                <th>Nama Akun</th>
                                <th>Total Debit</th>
                                <th>Total Kredit</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows_html}
                        </tbody>
                        <tfoot>
                            <tr>
                                <td><strong>TOTAL</strong></td>
                                <td class="debit"><strong>{rp(total_debit)}</strong></td>
                                <td class="kredit"><strong>{rp(total_kredit)}</strong></td>
                            </tr>
                        </tfoot>
                    </table>
                </div>
                
                <!-- Action Buttons -->
                <div class="action-buttons">
                    <a href="/dashboard" class="btn btn-primary">🏠 Dashboard</a>
                    <a href="/jurnal-umum" class="btn btn-secondary">📝 Jurnal Umum</a>
                    <a href="/laporan-keuangan" class="btn btn-success">📈 Laporan Keuangan</a>
                    <button onclick="window.print()" class="btn" style="background: #17a2b8;">🖨️ Cetak Laporan</button>
                </div>
            </div>
        </div>
        
        <script>
            // Add subtle animation to table rows
            document.addEventListener('DOMContentLoaded', function() {{
                const rows = document.querySelectorAll('.neraca-table tbody tr');
                rows.forEach((row, index) => {{
                    row.style.opacity = '0';
                    row.style.transform = 'translateY(10px)';
                    setTimeout(() => {{
                        row.style.transition = 'all 0.3s ease';
                        row.style.opacity = '1';
                        row.style.transform = 'translateY(0)';
                    }}, index * 50);
                }});
            }});
            
            // Highlight balanced/unbalanced status
            const balanceStatus = document.querySelector('.balance-status');
            if (balanceStatus.classList.contains('balance-correct')) {{
                setTimeout(() => {{
                    balanceStatus.style.transform = 'scale(1.02)';
                    balanceStatus.style.transition = 'transform 0.3s ease';
                }}, 500);
            }}
        </script>
    </body>
    </html>
    """
    return html

# ============================================================
# 🔹 ROUTE: Jurnal Penyesuaian 
# ============================================================
@app.route("/jurnal-penyesuaian", methods=["GET", "POST"])
def jurnal_penyesuaian():
    if not session.get('logged_in'):
        return redirect('/login')

    user_email = session.get('user_email')
    message = ""
    
    # Handle form submission untuk penyesuaian manual
    if request.method == "POST" and 'add_penyesuaian' in request.form:
        message = process_penyesuaian_manual(user_email)
    
    # Handle form submission untuk penyesuaian aset
    if request.method == "POST" and 'penyesuaian_aset' in request.form:
        message = process_penyesuaian_aset(user_email)

    # Handle generate otomatis
    if request.method == "POST" and 'generate_penyesuaian' in request.form:
        message = generate_penyesuaian_otomatis(user_email)
    
    # Ambil data jurnal penyesuaian
    jurnal_data = get_jurnal_penyesuaian_data()
    
    # Ambil data aset tetap untuk form penyesuaian
    aset_tetap_data = get_aset_tetap_data()
    
    # Hitung totals
    total_debit = sum(j.get("debit", 0) for j in jurnal_data)
    total_kredit = sum(j.get("kredit", 0) for j in jurnal_data)
    
    return generate_jurnal_penyesuaian_html(
        user_email, message, jurnal_data, aset_tetap_data, 
        total_debit, total_kredit
    )

def process_penyesuaian_manual(user_email):
    """Process penyesuaian manual dari form"""
    try:
        tanggal = request.form["tanggal"]
        akun_debit = request.form["akun_debit"]
        akun_kredit = request.form["akun_kredit"]
        jumlah = int(request.form["jumlah"])
        keterangan = request.form["keterangan"]
        
        if jumlah <= 0:
            return '<div class="message error">❌ Jumlah penyesuaian harus lebih dari 0!</div>'
        
        # Buat entri jurnal penyesuaian
        jurnal_entries = [
            {
                "tanggal": tanggal,
                "nama_akun": akun_debit,
                "ref": get_kode_akun(akun_debit),
                "debit": jumlah,
                "kredit": 0,
                "deskripsi": f"Penyesuaian: {keterangan}",
                "transaksi_type": "PENYESUAIAN_MANUAL",
                "user_email": user_email,
                "created_at": datetime.now().isoformat()
            },
            {
                "tanggal": tanggal,
                "nama_akun": akun_kredit,
                "ref": get_kode_akun(akun_kredit),
                "debit": 0,
                "kredit": jumlah,
                "deskripsi": f"Penyesuaian: {keterangan}",
                "transaksi_type": "PENYESUAIAN_MANUAL",
                "user_email": user_email,
                "created_at": datetime.now().isoformat()
            }
        ]
        
        # Simpan ke database
        success_count = 0
        for entry in jurnal_entries:
            try:
                result = supabase.table("jurnal_umum").insert(entry).execute()
                if result.data:
                    success_count += 1
            except Exception as e:
                logger.error(f"Error insert jurnal penyesuaian: {str(e)}")
        
        if success_count == len(jurnal_entries):
            return f'<div class="message success">✅ Penyesuaian manual berhasil dicatat!</div>'
        else:
            return f'<div class="message error">❌ Sebagian jurnal gagal disimpan ({success_count}/{len(jurnal_entries)})</div>'
            
    except Exception as e:
        logger.error(f"❌ Error proses penyesuaian manual: {str(e)}")
        return f'<div class="message error">❌ Error: {str(e)}</div>'

def process_penyesuaian_aset(user_email):
    """Process penyesuaian untuk penyusutan aset tetap"""
    try:
        tanggal = request.form["tanggal_aset"]
        aset_id = request.form["aset_id"]
        periode_bulan = int(request.form["periode_bulan"])
        
        # Ambil data aset
        aset_result = supabase.table("aset_tetap").select("*").eq("id", aset_id).execute()
        if not aset_result.data:
            return '<div class="message error">❌ Data aset tidak ditemukan!</div>'
        
        aset = aset_result.data[0]
        
        # Hitung penyusutan untuk periode tertentu
        penyusutan_per_bulan = aset['penyusutan_tahunan'] / 12
        total_penyusutan = penyusutan_per_bulan * periode_bulan
        
        # Cek apakah penyusutan melebihi nilai perolehan
        if total_penyusutan > aset['nilai_buku']:
            total_penyusutan = aset['nilai_buku']  # Jangan melebihi nilai buku
        
        if total_penyusutan <= 0:
            return '<div class="message error">❌ Tidak ada penyusutan yang perlu dicatat!</div>'
        
        # Buat jurnal penyesuaian penyusutan
        jurnal_entries = [
            {
                "tanggal": tanggal,
                "nama_akun": "Beban Penyusutan",
                "ref": "6130",
                "debit": total_penyusutan,
                "kredit": 0,
                "deskripsi": f"Penyusutan {aset['nama_aset']} ({periode_bulan} bulan)",
                "transaksi_type": "PENYESUAIAN_ASET",
                "user_email": user_email,
                "created_at": datetime.now().isoformat()
            },
            {
                "tanggal": tanggal,
                "nama_akun": "Akumulasi Penyusutan",
                "ref": get_kode_akumulasi_penyusutan(aset['jenis_aset']),
                "debit": 0,
                "kredit": total_penyusutan,
                "deskripsi": f"Akumulasi penyusutan {aset['nama_aset']}",
                "transaksi_type": "PENYESUAIAN_ASET",
                "user_email": user_email,
                "created_at": datetime.now().isoformat()
            }
        ]
        
        # Simpan jurnal
        success_count = 0
        for entry in jurnal_entries:
            try:
                result = supabase.table("jurnal_umum").insert(entry).execute()
                if result.data:
                    success_count += 1
            except Exception as e:
                logger.error(f"Error insert jurnal penyusutan: {str(e)}")
        
        # Update data aset
        if success_count == len(jurnal_entries):
            akumulasi_baru = aset['akumulasi_penyusutan'] + total_penyusutan
            nilai_buku_baru = aset['nilai_perolehan'] - akumulasi_baru
            
            update_data = {
                "akumulasi_penyusutan": akumulasi_baru,
                "nilai_buku": nilai_buku_baru,
                "updated_at": datetime.now().isoformat()
            }
            
            supabase.table("aset_tetap").update(update_data).eq("id", aset_id).execute()
            
            logger.info(f"✅ Penyesuaian penyusutan aset {aset['nama_aset']}: {total_penyusutan}")
            return f'<div class="message success">✅ Penyesuaian penyusutan berhasil! Nilai: {format_currency(total_penyusutan)}</div>'
        else:
            return f'<div class="message error">❌ Sebagian jurnal gagal disimpan</div>'
            
    except Exception as e:
        logger.error(f"❌ Error proses penyesuaian aset: {str(e)}")
        return f'<div class="message error">❌ Error: {str(e)}</div>'

def generate_penyesuaian_otomatis(user_email):
    """Generate penyesuaian otomatis untuk semua aset yang belum disusutkan"""
    try:
        # Ambil semua aset tetap
        aset_data = get_aset_tetap_data()
        
        if not aset_data:
            return '<div class="message info">ℹ Tidak ada data aset tetap untuk disesuaikan</div>'
        
        success_count = 0
        total_penyusutan = 0
        
        for aset in aset_data:
            # Hitung bulan sejak perolehan
            try:
                tgl_perolehan = datetime.strptime(aset['tanggal_perolehan'], '%Y-%m-%d')
                bulan_berjalan = (datetime.now() - tgl_perolehan).days // 30
            except:
                bulan_berjalan = 1
            
            # Skip jika belum 1 bulan
            if bulan_berjalan < 1:
                continue
            
            # Hitung penyusutan yang seharusnya
            penyusutan_per_bulan = aset['penyusutan_tahunan'] / 12
            penyusutan_seharusnya = penyusutan_per_bulan * bulan_berjalan
            
            # Penyusutan yang sudah dicatat
            penyusutan_sudah = aset['akumulasi_penyusutan']
            
            # Penyusutan yang belum dicatat
            penyusutan_belum = penyusutan_seharusnya - penyusutan_sudah
            
            if penyusutan_belum > 0:
                # Buat jurnal penyesuaian
                jurnal_entries = [
                    {
                        "tanggal": datetime.now().strftime('%Y-%m-%d'),
                        "nama_akun": "Beban Penyusutan",
                        "ref": "6130",
                        "debit": penyusutan_belum,
                        "kredit": 0,
                        "deskripsi": f"Penyusutan otomatis {aset['nama_aset']}",
                        "transaksi_type": "PENYESUAIAN_OTOMATIS",
                        "user_email": user_email,
                        "created_at": datetime.now().isoformat()
                    },
                    {
                        "tanggal": datetime.now().strftime('%Y-%m-%d'),
                        "nama_akun": "Akumulasi Penyusutan",
                        "ref": get_kode_akumulasi_penyusutan(aset['jenis_aset']),
                        "debit": 0,
                        "kredit": penyusutan_belum,
                        "deskripsi": f"Akumulasi penyusutan {aset['nama_aset']}",
                        "transaksi_type": "PENYESUAIAN_OTOMATIS",
                        "user_email": user_email,
                        "created_at": datetime.now().isoformat()
                    }
                ]
                
                # Simpan jurnal
                entry_success = 0
                for entry in jurnal_entries:
                    try:
                        result = supabase.table("jurnal_umum").insert(entry).execute()
                        if result.data:
                            entry_success += 1
                    except Exception as e:
                        logger.error(f"Error insert jurnal otomatis: {str(e)}")
                
                if entry_success == len(jurnal_entries):
                    # Update data aset
                    akumulasi_baru = aset['akumulasi_penyusutan'] + penyusutan_belum
                    nilai_buku_baru = aset['nilai_perolehan'] - akumulasi_baru
                    
                    update_data = {
                        "akumulasi_penyusutan": akumulasi_baru,
                        "nilai_buku": nilai_buku_baru,
                        "updated_at": datetime.now().isoformat()
                    }
                    
                    supabase.table("aset_tetap").update(update_data).eq("id", aset['id']).execute()
                    
                    success_count += 1
                    total_penyusutan += penyusutan_belum
        
        if success_count > 0:
            return f'<div class="message success">✅ Berhasil generate {success_count} penyesuaian penyusutan! Total: {format_currency(total_penyusutan)}</div>'
        else:
            return '<div class="message info">ℹ Tidak ada penyesuaian penyusutan yang diperlukan</div>'
            
    except Exception as e:
        logger.error(f"❌ Error generate penyesuaian otomatis: {str(e)}")
        return f'<div class="message error">❌ Error: {str(e)}</div>'

def get_kode_akun(nama_akun):
    """Get kode akun berdasarkan nama akun"""
    kode_map = {
        "Beban Penyusutan": "6130",
        "Beban Perlengkapan": "6110",
        "HPP": "5210",
        "Pembelian": "5110",
        "Akumulasi Penyusutan": "1260",
        "Perlengkapan": "1140",
        "Persediaan Barang Dagang": "1130",
    }
    return kode_map.get(nama_akun, "0000")

def get_kode_akumulasi_penyusutan(jenis_aset):
    """Get kode akun akumulasi penyusutan berdasarkan jenis aset"""
    kode_map = {
        "TANAH": "1261",
        "BANGUNAN": "1262",
        "KENDARAAN": "1263",
        "PERALATAN": "1264",
        "INVENTARIS": "1265"
    }
    return kode_map.get(jenis_aset, "1260")

def get_jurnal_penyesuaian_data():
    """Ambil data jurnal penyesuaian"""
    try:
        result = supabase.table("jurnal_umum")\
            .select("*")\
            .in_("transaksi_type", ["PENYESUAIAN_MANUAL", "PENYESUAIAN_ASET", "PENYESUAIAN_OTOMATIS"])\
            .order("tanggal", desc=True)\
            .execute()
        return result.data or []
    except Exception as e:
        logger.error(f"Error ambil data penyesuaian: {str(e)}")
        return []

def generate_jurnal_penyesuaian_html(user_email, message, jurnal_data, aset_tetap_data, total_debit, total_kredit):
    """Generate HTML untuk halaman jurnal penyesuaian"""
    
    def format_currency(amount):
        return f"Rp {amount:,.0f}".replace(",", ".")
    
    # Generate table rows
    rows_html = ""
    if jurnal_data:
        for jurnal in jurnal_data:
            rows_html += f"""
            <tr>
                <td>{jurnal['tanggal']}</td>
                <td>{jurnal['nama_akun']}</td>
                <td>{jurnal.get('deskripsi', '')}</td>
                <td class="number {'debit' if jurnal['debit'] > 0 else ''}">
                    {format_currency(jurnal['debit']) if jurnal['debit'] > 0 else '-'}
                </td>
                <td class="number {'kredit' if jurnal['kredit'] > 0 else ''}">
                    {format_currency(jurnal['kredit']) if jurnal['kredit'] > 0 else '-'}
                </td>
                <td>
                    <span class="badge {jurnal['transaksi_type'].lower()}">
                        {jurnal['transaksi_type'].replace('_', ' ').title()}
                    </span>
                </td>
            </tr>
            """
    else:
        rows_html = """
        <tr>
            <td colspan="6" class="empty-state">
                📊 Belum ada jurnal penyesuaian
            </td>
        </tr>
        """
    
    # Generate options untuk aset tetap
    aset_options = ""
    for aset in aset_tetap_data:
        aset_options += f"""
        <option value="{aset['id']}">
            {aset['nama_aset']} - {format_currency(aset['nilai_buku'])} (Penyusutan: {format_currency(aset['penyusutan_tahunan'])}/tahun)
        </option>
        """
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Jurnal Penyesuaian - PINKILANG</title>
        <meta charset="utf-8">
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: 'Arial', sans-serif;
                background: linear-gradient(135deg, #ffe6f2, #fff0f7);
                padding: 20px;
                min-height: 100vh;
            }}
            
            .container {{
                max-width: 1400px;
                margin: 0 auto;
                background: white;
                border-radius: 15px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                overflow: hidden;
            }}
            
            .header {{
                background: linear-gradient(135deg, #ff85b3, #ff66a3);
                color: white;
                padding: 25px;
                text-align: center;
            }}
            
            .back-btn {{
                display: inline-block;
                padding: 10px 20px;
                background: rgba(255,255,255,0.2);
                color: white;
                text-decoration: none;
                border-radius: 8px;
                margin-bottom: 15px;
                border: 1px solid rgba(255,255,255,0.3);
            }}
            
            h1 {{
                font-size: 28px;
                margin-bottom: 10px;
            }}
            
            .content {{
                padding: 25px;
            }}
            
            .section {{
                margin: 25px 0;
                padding: 20px;
                background: #fff5f9;
                border-radius: 12px;
                border-left: 5px solid #ff85b3;
            }}
            
            .section-title {{
                color: #ff66a3;
                font-size: 22px;
                margin-bottom: 20px;
                padding-bottom: 10px;
                border-bottom: 2px solid #ffe6f2;
            }}
            
            .form-grid {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
                margin-bottom: 20px;
            }}
            
            .form-group {{
                margin-bottom: 15px;
            }}
            
            label {{
                display: block;
                margin-bottom: 5px;
                color: #d63384;
                font-weight: bold;
            }}
            
            input, select, textarea {{
                width: 100%;
                padding: 10px;
                border: 2px solid #ffd1e6;
                border-radius: 8px;
                font-size: 14px;
            }}
            
            .btn {{
                padding: 12px 25px;
                background: linear-gradient(135deg, #ff85b3, #ff66a3);
                color: white;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                font-size: 16px;
                margin: 5px;
            }}
            
            .btn:hover {{
                background: linear-gradient(135deg, #ff66a3, #ff4d94);
            }}
            
            .btn-secondary {{
                background: linear-gradient(135deg, #66b3ff, #4d94ff);
            }}
            
            .btn-success {{
                background: linear-gradient(135deg, #00cc66, #00b359);
            }}
            
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 15px;
                background: white;
                border-radius: 8px;
                overflow: hidden;
            }}
            
            th, td {{
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid #ffe6f2;
            }}
            
            th {{
                background: #ff85b3;
                color: white;
                font-weight: bold;
            }}
            
            .number {{
                text-align: right;
                font-family: 'Courier New', monospace;
            }}
            
            .debit {{
                color: #009933;
                font-weight: bold;
            }}
            
            .kredit {{
                color: #cc0000;
                font-weight: bold;
            }}
            
            .badge {{
                padding: 4px 8px;
                border-radius: 12px;
                font-size: 11px;
                font-weight: bold;
                color: white;
            }}
            
            .badge.penyesuaian_manual {{ background: #66b3ff; }}
            .badge.penyesuaian_aset {{ background: #00cc66; }}
            .badge.penyesuaian_otomatis {{ background: #ff9966; }}
            
            .total-row {{
                background: #ffe6f2;
                font-weight: bold;
            }}
            
            .info-box {{
                background: #e6f7ff;
                border: 1px solid #91d5ff;
                border-radius: 8px;
                padding: 15px;
                margin: 15px 0;
                color: #0066cc;
            }}
            
            .message {{
                padding: 15px;
                margin: 15px 0;
                border-radius: 8px;
            }}
            
            .success {{
                background: #d4edda;
                color: #155724;
                border: 1px solid #c3e6cb;
            }}
            
            .error {{
                background: #f8d7da;
                color: #721c24;
                border: 1px solid #f5c6cb;
            }}
            
            .empty-state {{
                text-align: center;
                padding: 40px;
                color: #999;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <!-- Header -->
            <div class="header">
                <a href="/dashboard" class="back-btn">← Kembali ke Dashboard</a>
                <h1>🔄 Jurnal Penyesuaian</h1>
                <p>Terintegrasi dengan Modul Aset - PINKILANG</p>
            </div>
            
            <!-- Content -->
            <div class="content">
                {message}
                
                <!-- Form Penyesuaian Manual -->
                <div class="section">
                    <h2 class="section-title">📝 Penyesuaian Manual</h2>
                    
                    <form method="POST">
                        <div class="form-grid">
                            <div class="form-group">
                                <label for="tanggal">📅 Tanggal Penyesuaian:</label>
                                <input type="date" id="tanggal" name="tanggal" 
                                       value="{datetime.now().strftime('%Y-%m-%d')}" required>
                            </div>
                            <div class="form-group">
                                <label for="akun_debit">💚 Akun Debit:</label>
                                <select id="akun_debit" name="akun_debit" required>
                                    <option value="">Pilih Akun Debit</option>
                                    <option value="Beban Penyusutan">Beban Penyusutan</option>
                                    <option value="Beban Perlengkapan">Beban Perlengkapan</option>
                                    <option value="HPP">HPP</option>
                                    <option value="Persediaan Barang Dagang">Persediaan Barang Dagang</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label for="akun_kredit">❤ Akun Kredit:</label>
                                <select id="akun_kredit" name="akun_kredit" required>
                                    <option value="">Pilih Akun Kredit</option>
                                    <option value="Akumulasi Penyusutan">Akumulasi Penyusutan</option>
                                    <option value="Perlengkapan">Perlengkapan</option>
                                    <option value="Persediaan Barang Dagang">Persediaan Barang Dagang</option>
                                    <option value="Pembelian">Pembelian</option>
                                    <option value="HPP">HPP</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label for="jumlah">💰 Jumlah Penyesuaian (Rp):</label>
                                <input type="number" id="jumlah" name="jumlah" 
                                       placeholder="0" step="1" min="1" required>
                            </div>
                            <div class="form-group" style="grid-column: span 2;">
                                <label for="keterangan">📋 Keterangan Penyesuaian:</label>
                                <textarea id="keterangan" name="keterangan" 
                                          placeholder="Jelaskan alasan penyesuaian..." required></textarea>
                            </div>
                        </div>
                        <button type="submit" name="add_penyesuaian" class="btn">💾 Simpan Penyesuaian Manual</button>
                    </form>
                </div>
                
                <!-- Form Penyesuaian Aset -->
                <div class="section">
                    <h2 class="section-title">🏢 Penyesuaian Penyusutan Aset</h2>
                    
                    <form method="POST">
                        <div class="form-grid">
                            <div class="form-group">
                                <label for="tanggal_aset">📅 Tanggal Penyesuaian:</label>
                                <input type="date" id="tanggal_aset" name="tanggal_aset" 
                                       value="{datetime.now().strftime('%Y-%m-%d')}" required>
                            </div>
                            <div class="form-group">
                                <label for="aset_id">🏗 Pilih Aset Tetap:</label>
                                <select id="aset_id" name="aset_id" required>
                                    <option value="">Pilih Aset Tetap</option>
                                    {aset_options if aset_tetap_data else '<option value="">Tidak ada data aset</option>'}
                                </select>
                            </div>
                            <div class="form-group">
                                <label for="periode_bulan">⏰ Periode Penyusutan (bulan):</label>
                                <input type="number" id="periode_bulan" name="periode_bulan" 
                                       value="1" min="1" max="12" required>
                            </div>
                        </div>
                        <button type="submit" name="penyesuaian_aset" class="btn btn-success" 
                                {"disabled" if not aset_tetap_data else ""}>
                            📊 Hitung & Simpan Penyusutan
                        </button>
                    </form>
                </div>
                
                <!-- Generate Otomatis -->
                <div class="section" style="text-align: center;">
                    <h2 class="section-title">⚡ Penyesuaian Otomatis</h2>
                    <p>Generate penyesuaian penyusutan untuk semua aset tetap secara otomatis</p>
                    
                    <form method="POST">
                        <button type="submit" name="generate_penyesuaian" class="btn btn-secondary">
                            🔄 Generate Penyesuaian Otomatis
                        </button>
                    </form>
                </div>
                
                <!-- Daftar Jurnal Penyesuaian -->
                <div class="section">
                    <h2 class="section-title">📋 Daftar Jurnal Penyesuaian</h2>
                    
                    <table>
                        <thead>
                            <tr>
                                <th>Tanggal</th>
                                <th>Akun</th>
                                <th>Keterangan</th>
                                <th>Debit</th>
                                <th>Kredit</th>
                                <th>Jenis</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows_html}
                            <tr class="total-row">
                                <td colspan="3"><strong>TOTAL</strong></td>
                                <td class="number debit"><strong>{format_currency(total_debit)}</strong></td>
                                <td class="number kredit"><strong>{format_currency(total_kredit)}</strong></td>
                                <td></td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                
                <!-- Action Buttons -->
                <div style="text-align: center; margin-top: 30px;">
                    <a href="/aset-tetap" class="btn btn-secondary">🏢 Kelola Aset Tetap</a>
                    <a href="/jurnal-umum" class="btn">📝 Lihat Jurnal Umum</a>
                    <a href="/neraca-saldo-setelah-penyesuaian" class="btn btn-success">🏦 Lihat NSSP</a>
                    <button onclick="window.print()" class="btn">🖨 Cetak Laporan</button>
                </div>
            </div>
        </div>

    </body>
    </html>
    """
    return html

def hitung_penyusutan_otomatis():
    """Hitung total penyusutan yang perlu disesuaikan"""
    try:
        aset_data = get_aset_tetap_data()
        total_penyusutan = 0
        
        for aset in aset_data:
            try:
                tgl_perolehan = datetime.strptime(aset['tanggal_perolehan'], '%Y-%m-%d')
                bulan_berjalan = (datetime.now() - tgl_perolehan).days // 30
                
                if bulan_berjalan > 0:
                    penyusutan_per_bulan = aset['penyusutan_tahunan'] / 12
                    penyusutan_seharusnya = penyusutan_per_bulan * bulan_berjalan
                    penyusutan_belum = penyusutan_seharusnya - aset['akumulasi_penyusutan']
                    
                    if penyusutan_belum > 0:
                        total_penyusutan += penyusutan_belum
            except:
                continue
        
        return total_penyusutan
    except Exception as e:
        logger.error(f"Error hitung penyusutan otomatis: {str(e)}")
        return 0

# ============================================================
# 🔹 ROUTE: Generate Penyesuaian Otomatis
# ============================================================
@app.route("/generate-penyesuaian-otomatis")
def generate_penyesuaian_otomatis():
    if not session.get('logged_in'):
        return redirect('/login')

    user_email = session.get('user_email')
    return redirect("/jurnal-penyesuaian")

@app.route("/laporan-keuangan")
def laporan_keuangan():
    if not session.get('logged_in'):
        return redirect('/login')
    return create_simple_page("📈 Laporan Keuangan", "📈 Halaman Laporan Keuangan akan segera hadir! 📈")

@app.route("/jurnal-penutup")
def jurnal_penutup():
    if not session.get('logged_in'):
        return redirect('/login')
    return create_simple_page("🔒 Jurnal Penutup", "🔒 Halaman Jurnal Penutup akan segera hadir! 🔒")

# ============================================================
# 🔹 ROUTE: Operasional (PENGELUARAN BIAYA OPERASIONAL) 
# ============================================================
@app.route("/operasional", methods=["GET", "POST"])
def operasional():
    if not session.get('logged_in'):
        return redirect('/login')
    
    user_id = session.get('user_id')
    user_email = session.get('user_email')
    message = ""
    
    # Handle form submission untuk transaksi operasional
    if request.method == "POST" and 'add_operasional' in request.form:
        message = process_operasional_form(user_id, user_email)
    
    # Handle generate jurnal otomatis
    if request.method == "POST" and 'generate_jurnal' in request.form:
        message = generate_jurnal_operasional_otomatis(user_email)
    
    # Ambil data transaksi operasional dari SEMUA USER
    transaksi_operasional, total_pengeluaran_all = get_operasional_data()
    
    # Hitung pengeluaran per kategori
    pengeluaran_per_kategori = calculate_pengeluaran_per_kategori(transaksi_operasional)
    
    # Hitung jurnal yang belum dibuat
    status_jurnal = hitung_jurnal_yang_belum_dibuat()
    
    # Generate HTML
    return generate_operasional_html(
        user_email, 
        message, 
        transaksi_operasional, 
        total_pengeluaran_all, 
        pengeluaran_per_kategori,
        status_jurnal
    )

def process_operasional_form(user_id, user_email):
    """Process operasional form submission """
    try:
        # Collect form data
        form_data = {
            "tanggal": request.form["tanggal"],
            "jenis_pengeluaran": request.form["jenis_pengeluaran"],
            "nama_barang": request.form["nama_barang"],
            "jumlah": float(request.form["jumlah"]),
            "satuan": request.form["satuan"],
            "harga_satuan": int(request.form["harga_satuan"]),
            "supplier": request.form["supplier"],
            "metode_pembayaran": request.form["metode_pembayaran"],
            "keterangan": request.form["keterangan"]
        }
        
        # Validasi jenis pengeluaran
        jenis_beban_valid = ['PERLENGKAPAN','LISTRIK_AIR_TELEPON', 'PENYUSUTAN', 'LAIN_LAIN']
        if form_data["jenis_pengeluaran"] not in jenis_beban_valid:
            return '<div class="message error">❌ Jenis pengeluaran tidak valid!</div>'
        
        # Calculate total
        total_pengeluaran = form_data["jumlah"] * form_data["harga_satuan"]
        
        if total_pengeluaran <= 0:
            return '<div class="message error">❌ Total pengeluaran harus lebih dari 0!</div>'
        
        # Prepare transaction data
        transaksi_data = {
            "user_id": user_id,
            "user_email": user_email,
            "tanggal": form_data["tanggal"],
            "jenis_pengeluaran": form_data["jenis_pengeluaran"],
            "nama_barang": form_data["nama_barang"],
            "jumlah": form_data["jumlah"],
            "satuan": form_data["satuan"],
            "harga_satuan": form_data["harga_satuan"],
            "total_pengeluaran": total_pengeluaran,
            "supplier": form_data["supplier"],
            "metode_pembayaran": form_data["metode_pembayaran"],
            "keterangan": form_data["keterangan"],
            "created_at": datetime.now().isoformat()
        }
        
        # Insert to database
        if supabase:
            insert_result = supabase.table("operasional").insert(transaksi_data).execute()
            
            # Create journal entries if insertion successful
            if insert_result and insert_result.data:
                transaksi_id = insert_result.data[0]['id']
                
                # 🎯 BUAT JURNAL OTOMATIS
                journal_data = {
                    'tanggal': form_data["tanggal"],
                    'jenis_pengeluaran': form_data["jenis_pengeluaran"],
                    'nama_barang': form_data["nama_barang"],
                    'total_pengeluaran': total_pengeluaran,
                    'metode_pembayaran': form_data["metode_pembayaran"],
                    'supplier': form_data["supplier"],
                    'transaksi_id': transaksi_id
                }
                
                # Panggil fungsi create_journal_entries
                result = create_journal_entries("OPERASIONAL", journal_data, user_email)
                
                if result:
                    logger.info(f"✅ Jurnal operasional berhasil dibuat untuk transaksi {transaksi_id}")
                    return f'<div class="message success">✅ Pengeluaran operasional berhasil dicatat! Jurnal otomatis dibuat.</div>'
                else:
                    logger.warning(f"⚠️ Gagal membuat jurnal untuk operasional ID: {transaksi_id}")
                    return f'<div class="message success">✅ Pengeluaran operasional berhasil dicatat! (Catatan: Gagal membuat jurnal)</div>'
            else:
                return '<div class="message error">❌ Gagal menyimpan data operasional!</div>'
        else:
            return '<div class="message error">❌ Database tidak tersedia!</div>'
                
    except Exception as e:
        logger.error(f"❌ Error tambah pengeluaran operasional: {str(e)}")
        return f'<div class="message error">❌ Error mencatat pengeluaran: {str(e)}</div>'

def generate_jurnal_operasional_otomatis(user_email):
    """Generate jurnal untuk semua transaksi operasional yang belum memiliki jurnal"""
    try:
        # Ambil semua transaksi operasional yang belum memiliki jurnal
        operasional_data = supabase.table("operasional").select("*").execute().data or []
        
        success_count = 0
        total_processed = 0
        
        for operasional in operasional_data:
            # Cek apakah sudah ada jurnal untuk transaksi ini
            existing_journal = supabase.table("jurnal_umum")\
                .select("*")\
                .eq("transaksi_id", operasional['id'])\
                .eq("transaksi_type", "OPERASIONAL")\
                .execute()
            
            if not existing_journal.data:  # Hanya buat jika belum ada
                journal_data = {
                    'tanggal': operasional['tanggal'],
                    'jenis_pengeluaran': operasional['jenis_pengeluaran'],
                    'nama_barang': operasional['nama_barang'],
                    'total_pengeluaran': operasional['total_pengeluaran'],
                    'metode_pembayaran': operasional['metode_pembayaran'],
                    'supplier': operasional.get('supplier', ''),
                    'transaksi_id': operasional['id']
                }
                
                if create_journal_entries("OPERASIONAL", journal_data, user_email):
                    success_count += 1
                    logger.info(f"✅ Jurnal otomatis dibuat untuk operasional ID: {operasional['id']}")
                
                total_processed += 1
        
        if total_processed > 0:
            return f'<div class="message success">✅ Berhasil membuat {success_count} jurnal dari {total_processed} transaksi operasional!</div>'
        else:
            return '<div class="message info">ℹ️ Semua transaksi operasional sudah memiliki jurnal.</div>'
            
    except Exception as e:
        logger.error(f"❌ Error generate jurnal operasional: {str(e)}")
        return f'<div class="message error">❌ Error generate jurnal: {str(e)}</div>'

def get_operasional_data():
    """Get operasional data from database"""
    transaksi_operasional = []
    total_pengeluaran_all = 0
    
    try:
        if supabase:
            result = supabase.table("operasional").select("*").order("tanggal", desc=True).execute()
            transaksi_operasional = result.data
            
            # Calculate total pengeluaran
            for transaksi in transaksi_operasional:
                total_pengeluaran_all += transaksi['total_pengeluaran']
                
    except Exception as e:
        logger.error(f"Error ambil data operasional: {str(e)}")
        transaksi_operasional = []
    
    return transaksi_operasional, total_pengeluaran_all

def calculate_pengeluaran_per_kategori(transaksi_operasional):
    """Calculate pengeluaran per kategori"""
    pengeluaran_per_kategori = {}
    for transaksi in transaksi_operasional:
        kategori = transaksi['jenis_pengeluaran']
        if kategori in pengeluaran_per_kategori:
            pengeluaran_per_kategori[kategori] += transaksi['total_pengeluaran']
        else:
            pengeluaran_per_kategori[kategori] = transaksi['total_pengeluaran']
    
    return pengeluaran_per_kategori

def hitung_jurnal_yang_belum_dibuat():
    try:
        # Ambil semua transaksi operasional
        operasional_data = supabase.table("operasional").select("id").execute().data or []
        
        total_transaksi = len(operasional_data)
        total_belum_jurnal = 0
        
        for transaksi in operasional_data:
            if not cek_jurnal_operasional(transaksi['id']):
                total_belum_jurnal += 1
        
        return {
            'total_transaksi': total_transaksi,
            'total_belum_jurnal': total_belum_jurnal,
            'total_sudah_jurnal': total_transaksi - total_belum_jurnal
        }
        
    except Exception as e:
        logger.error(f"Error hitung jurnal belum dibuat: {str(e)}")
        return {'total_transaksi': 0, 'total_belum_jurnal': 0, 'total_sudah_jurnal': 0}

def cek_jurnal_operasional(transaksi_id):
    try:
        result = supabase.table("jurnal_umum")\
            .select("*")\
            .eq("transaksi_id", transaksi_id)\
            .eq("transaksi_type", "OPERASIONAL")\
            .execute()
        
        return len(result.data) > 0
    except Exception as e:
        logger.error(f"Error cek jurnal operasional: {str(e)}")
        return False

def generate_transaction_rows(transaksi_operasional, user_email):
    if not transaksi_operasional:
        return '''
        <tr>
            <td colspan="10" style="text-align: center; padding: 40px; color: #ff85b3;">
                💝 Belum ada transaksi operasional
            </td>
        </tr>
        '''
    
    rows = []
    for t in transaksi_operasional:
        # Cek status jurnal
        has_jurnal = cek_jurnal_operasional(t['id'])
        jurnal_status = '<span class="jurnal-status jurnal-ada">✅ JURNAL</span>' if has_jurnal else '<span class="jurnal-status jurnal-tidak">❌ BELUM</span>'
        
        # Determine account name based on jenis_pengeluaran
        account_map = {
            'LISTRIK_AIR_TELEPON': 'Beban TLA',
            'PERLENGKAPAN': 'Beban Perlengkapan',
            'PENYUSUTAN': 'Beban Penyusutan',
            'LAIN_LAIN': 'Beban Lain - Lain'
        }
        account_name = account_map.get(t['jenis_pengeluaran'], 'Beban Operasional')
        
        row = f"""
        <tr>
            <td>{datetime.strptime(t['tanggal'], '%Y-%m-%d').strftime('%d/%m/%Y')}</td>
            <td>
                <span class="user-badge {'current-user' if t.get('user_email') == user_email else ''}">
                    {t.get('user_email', 'Unknown').split('@')[0]}
                </span>
            </td>
            <td>
                <span class="kategori-badge kategori-{t['jenis_pengeluaran'].lower()}">
                    {t['jenis_pengeluaran'].replace('_', ' ').title()}
                </span>
            </td>
            <td>
                <strong>{t['nama_barang']}</strong>
                {f"<br><small style='color: #666;'>{t['keterangan']}</small>" if t.get('keterangan') else ''}
            </td>
            <td>{t['jumlah']} {t.get('satuan', 'ekor')}</td>
            <td>{format_currency(t['harga_satuan'])}</td>
            <td>
                <span class="payment-badge {'cash' if t.get('metode_pembayaran') == 'CASH' else 'kredit'}">
                    {'💰 CASH' if t.get('metode_pembayaran') == 'CASH' else '📄 KREDIT'}
                </span>
            </td>
            <td>{t.get('supplier', '-')}</td>
            <td><strong style="color: #ff6666;">{format_currency(t['total_pengeluaran'])}</strong></td>
            <td>
                <small style="color: #666;">{account_name}</small>
                <br>{jurnal_status}
            </td>
        </tr>
        """
        rows.append(row)
    
    return "".join(rows)

def generate_kategori_breakdown(pengeluaran_per_kategori):
    """Generate kategori breakdown"""
    if not pengeluaran_per_kategori:
        return '''
        <div style="text-align: center; padding: 20px; color: #999;">
            📊 Belum ada data pengeluaran
        </div>
        '''
    
    breakdown_html = ""
    for kategori, jumlah in pengeluaran_per_kategori.items():
        breakdown_html += f"""
        <div style="background: white; padding: 15px; border-radius: 10px; border-left: 4px solid #ff85b3;">
            <div style="font-weight: bold; color: #ff66a3;">{kategori.replace('_', ' ').title()}</div>
            <div style="font-size: 18px; font-weight: bold;">{format_currency(jumlah)}</div>
        </div>
        """
    return breakdown_html

def generate_operasional_html(user_email, message, transaksi_operasional, total_pengeluaran_all, pengeluaran_per_kategori, status_jurnal):
    """Generate HTML untuk halaman operasional - VERSI FINAL"""
    
    def format_currency(amount):
        """Format currency to Indonesian format"""
        return f"Rp {amount:,.0f}".replace(",", ".")
    
    # Generate transaction rows
    transaction_rows = generate_transaction_rows(transaksi_operasional, user_email)
    
    # Generate kategori breakdown
    kategori_breakdown = generate_kategori_breakdown(pengeluaran_per_kategori)
    
    # Status jurnal info
    jurnal_info = ""
    if status_jurnal['total_transaksi'] > 0:
        jurnal_info = f"""
        <div class="info-box" style="background: {'#ffe6e6' if status_jurnal['total_belum_jurnal'] > 0 else '#e6ffe6'}; 
                                     border: 1px solid {'#ff6666' if status_jurnal['total_belum_jurnal'] > 0 else '#00cc66'};">
            <strong>📊 Status Jurnal:</strong> 
            {status_jurnal['total_sudah_jurnal']} transaksi sudah memiliki jurnal | 
            {status_jurnal['total_belum_jurnal']} transaksi belum memiliki jurnal
            {f'<br><form method="POST" style="margin-top: 10px;"><button type="submit" name="generate_jurnal" class="btn" style="background: #ff6666;">🔄 GENERATE JURNAL OTOMATIS</button></form>' if status_jurnal['total_belum_jurnal'] > 0 else ''}
        </div>
        """
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Operasional - PINKILANG</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: 'Arial Rounded MT Bold', 'Arial', sans-serif;
                background: linear-gradient(135deg, #ffe6f2, #fff0f7);
                min-height: 100vh;
                padding: 20px;
            }}
            
            .container {{
                max-width: 1400px;
                margin: 0 auto;
                background: white;
                border-radius: 20px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                overflow: hidden;
            }}
            
            .header {{
                background: linear-gradient(135deg, #ff85b3, #ff66a3);
                color: white;
                padding: 30px;
                text-align: center;
            }}
            
            .back-btn {{
                display: inline-block;
                padding: 10px 20px;
                background: rgba(255,255,255,0.2);
                color: white;
                text-decoration: none;
                border-radius: 10px;
                margin-bottom: 20px;
                border: 1px solid rgba(255,255,255,0.3);
            }}
            
            .back-btn:hover {{
                background: rgba(255,255,255,0.3);
            }}
            
            h1 {{
                font-size: 36px;
                margin-bottom: 10px;
            }}
            
            .content {{
                padding: 30px;
            }}
            
            .section {{
                margin-bottom: 40px;
                padding: 25px;
                background: #fff5f9;
                border-radius: 15px;
                border-left: 5px solid #ff85b3;
                box-shadow: 0 4px 15px rgba(255,133,179,0.1);
            }}
            
            .section-title {{
                color: #ff66a3;
                font-size: 24px;
                margin-bottom: 20px;
                padding-bottom: 10px;
                border-bottom: 2px solid #ffe6f2;
            }}
            
            .form-grid {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
                margin-bottom: 20px;
            }}
            
            .form-group {{
                margin-bottom: 15px;
            }}
            
            label {{
                display: block;
                margin-bottom: 5px;
                color: #d63384;
                font-weight: bold;
            }}
            
            input, select, textarea {{
                width: 100%;
                padding: 12px;
                border: 2px solid #ffd1e6;
                border-radius: 10px;
                font-size: 16px;
                transition: border-color 0.3s ease;
                background: white;
            }}
            
            input:focus, select:focus, textarea:focus {{
                border-color: #ff66a3;
                outline: none;
                box-shadow: 0 0 0 3px rgba(255,102,163,0.1);
            }}
            
            .btn {{
                padding: 12px 30px;
                background: linear-gradient(135deg, #ff85b3, #ff66a3);
                color: white;
                border: none;
                border-radius: 10px;
                cursor: pointer;
                font-size: 16px;
                transition: all 0.3s ease;
                font-weight: bold;
            }}
            
            .btn:hover {{
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(255,102,163,0.3);
                background: linear-gradient(135deg, #ff66a3, #ff4d94);
            }}
            
            .btn-secondary {{
                background: linear-gradient(135deg, #66b3ff, #4d94ff);
            }}
            
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin: 20px 0;
            }}
            
            .stat-card {{
                background: white;
                padding: 20px;
                border-radius: 10px;
                text-align: center;
                box-shadow: 0 4px 15px rgba(255,133,179,0.1);
                border: 1px solid #ffe6f2;
                transition: transform 0.3s ease;
            }}
            
            .stat-card:hover {{
                transform: translateY(-5px);
            }}
            
            .stat-number {{
                font-size: 24px;
                font-weight: bold;
                color: #ff66a3;
                margin: 10px 0;
            }}
            
            .stat-label {{
                color: #e83e8c;
                font-size: 14px;
                font-weight: bold;
            }}
            
            .table-container {{
                overflow-x: auto;
                margin-top: 20px;
            }}
            
            table {{
                width: 100%;
                border-collapse: collapse;
                background: white;
                border-radius: 10px;
                overflow: hidden;
                box-shadow: 0 4px 15px rgba(255,133,179,0.1);
            }}
            
            th, td {{
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid #ffe6f2;
                font-size: 14px;
            }}
            
            th {{
                background: linear-gradient(135deg, #ff85b3, #ff66a3);
                color: white;
                font-weight: bold;
            }}
            
            tr:hover {{
                background: #fff5f9;
            }}
            
            .user-badge {{
                background: #ffb6d9;
                color: #c2185b;
                padding: 4px 8px;
                border-radius: 12px;
                font-size: 12px;
                font-weight: bold;
            }}
            
            .current-user {{
                background: #ff66a3;
                color: white;
            }}
            
            .kategori-badge {{
                padding: 4px 8px;
                border-radius: 8px;
                font-size: 11px;
                font-weight: bold;
                color: white;
            }}
            
            .kategori-listrik_air_telepon {{ background: #66b3ff; }}
            .kategori-perlengkapan {{ background: #00cc66; }}
            .kategori-peralatan {{ background: #ffb366; }}
            
            .message {{
                padding: 15px;
                margin: 15px 0;
                border-radius: 10px;
                font-size: 14px;
            }}
            
            .success {{
                background: #d4edda;
                color: #155724;
                border: 1px solid #c3e6cb;
            }}
            
            .error {{
                background: #f8d7da;
                color: #721c24;
                border: 1px solid #f5c6cb;
            }}
            
            .info {{
                background: #d1ecf1;
                color: #0c5460;
                border: 1px solid #bee5eb;
            }}
            
            .info-box {{
                background: #ffe6f2;
                border: 1px solid #ffb6d9;
                border-radius: 10px;
                padding: 15px;
                margin: 15px 0;
                color: #d63384;
            }}
            
            .payment-badge {{
                background: #66b3ff;
                color: white;
                padding: 4px 8px;
                border-radius: 8px;
                font-size: 11px;
                font-weight: bold;
            }}
            
            .payment-badge.cash {{ background: #00cc66; }}
            .payment-badge.kredit {{ background: #ff6666; }}
            
            .akun-info {{
                background: #e6f7ff;
                border: 1px solid #b3e0ff;
                border-radius: 8px;
                padding: 10px;
                margin: 5px 0;
                font-size: 12px;
                color: #0066cc;
            }}
            
            .akun-guide {{
                background: #fff5f9;
                border: 1px solid #ffd1e6;
                border-radius: 10px;
                padding: 15px;
                margin: 15px 0;
            }}
            
            .akun-item {{
                padding: 5px 0;
                border-bottom: 1px dashed #ffd1e6;
            }}
            
            .akun-item:last-child {{
                border-bottom: none;
            }}
            
            .jurnal-status {{
                padding: 8px 12px;
                border-radius: 20px;
                font-size: 11px;
                font-weight: bold;
            }}
            
            .jurnal-ada {{ background: #d4ffd4; color: #006600; }}
            .jurnal-tidak {{ background: #ffd4d4; color: #cc0000; }}
        </style>
    </head>
    <body>
        <div class="container">
            <!-- Header -->
            <div class="header">
                <a href="/dashboard" class="back-btn">← Kembali ke Dashboard</a>
                <h1>💰 Modul Operasional</h1>
                <p>Pencatatan Pengeluaran Biaya Operasional - PINKILANG</p>
                <div style="margin-top: 10px; font-size: 14px; opacity: 0.9;">
                    👋 Login sebagai: <strong>{user_email}</strong>
                </div>
            </div>
            
            <!-- Content -->
            <div class="content">
                {message}
                
                {jurnal_info}
                <!-- Input Transaksi Operasional Section -->
                <div class="section">
                    <h2 class="section-title">➕ Input Pengeluaran Operasional</h2>
                    
                    <form method="POST">
                        <div class="form-grid">
                            <div class="form-group">
                                <label for="tanggal">📅 Tanggal Pengeluaran:</label>
                                <input type="date" id="tanggal" name="tanggal" 
                                       value="{datetime.now().strftime('%Y-%m-%d')}" required>
                            </div>
                            <div class="form-group">
                                <label for="jenis_pengeluaran">🏷️ Jenis Pengeluaran:</label>
                                <select id="jenis_pengeluaran" name="jenis_pengeluaran" required>
                                    <option value="">Pilih Jenis</option>
                                    <option value="PERLENGKAPAN">📦 Perlengkapan</option>
                                    <option value="PERALATAN">🛠️ Peralatan</option>
                                    <option value="LISTRIK_AIR_TELEPON">⚡TLA</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label for="nama_barang">📦 Nama Barang/Jasa:</label>
                                <input type="text" id="nama_barang" name="nama_barang" 
                                       placeholder="Contoh: Token Listrik, Alat Tulis, Peralatan Kantor" required>
                            </div>
                            <div class="form-group">
                                <label for="supplier">🏭 Supplier/Penyedia:</label>
                                <input type="text" id="supplier" name="supplier" 
                                       placeholder="Nama supplier atau penyedia jasa">
                            </div>
                            <div class="form-group">
                                <label for="jumlah">🔢 Jumlah:</label>
                                <input type="number" id="jumlah" name="jumlah" 
                                       placeholder="0" step="1" min="0" required>
                            </div>
                            <div class="form-group">
                                <label for="satuan">📏 Satuan:</label>
                                <select id="satuan" name="satuan" required>
                                    <option value="kwh">kwh</option>
                                    <option value="ekor">ekor</option>
                                    <option value="paket">paket</option>
                                    <option value="bulan">bulan</option>
                                    <option value="buah">buah</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label for="harga_satuan">💵 Harga Satuan (Rp):</label>
                                <input type="number" id="harga_satuan" name="harga_satuan" 
                                       placeholder="0" step="1" min="0" required>
                            </div>
                            <div class="form-group">
                                <label for="metode_pembayaran">💳 Metode Pembayaran:</label>
                                <select id="metode_pembayaran" name="metode_pembayaran" required>
                                    <option value="CASH">💰 Cash</option>
                                    <option value="KREDIT">📄 Kredit</option>
                                </select>
                            </div>
                            <div class="form-group" style="grid-column: span 2;">
                                <label for="keterangan">📝 Keterangan (Opsional):</label>
                                <textarea id="keterangan" name="keterangan" 
                                          placeholder="Tambahkan keterangan jika diperlukan..." rows="2"></textarea>
                            </div>
                        </div>
                        
                        <!-- Info Akun yang Akan Terpengaruh -->
                        <div class="akun-info">
                            <strong>💡 Info:</strong> Sistem akan otomatis membuat jurnal akuntansi sesuai dengan jenis pengeluaran yang dipilih.
                            Lihat panduan di atas untuk detail akun yang akan terpengaruh.
                        </div>
                        
                        <button type="submit" name="add_operasional" class="btn">💾 Catat Pengeluaran</button>
                    </form>
                </div>
                
                <!-- Ringkasan Pengeluaran -->
                <div class="section">
                    <h2 class="section-title">📊 Ringkasan Pengeluaran Operasional</h2>
                    <div class="stats-grid">
                        <div class="stat-card">
                            <div>💰</div>
                            <div class="stat-number">{format_currency(total_pengeluaran_all)}</div>
                            <div class="stat-label">Total Pengeluaran</div>
                        </div>
                        <div class="stat-card">
                            <div>📋</div>
                            <div class="stat-number">{len(transaksi_operasional)}</div>
                            <div class="stat-label">Total Transaksi</div>
                        </div>
                        <div class="stat-card">
                            <div>👥</div>
                            <div class="stat-number">{len(set(t['user_email'] for t in transaksi_operasional)) if transaksi_operasional else 0}</div>
                            <div class="stat-label">User Aktif</div>
                        </div>
                    </div>
                    
                    <!-- Breakdown per Kategori -->
                    <h3 style="color: #ff66a3; margin: 20px 0 10px 0;">📈 Breakdown per Kategori</h3>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px;">
                        {kategori_breakdown}
                    </div>
                </div>
                
                <!-- Daftar Transaksi Operasional -->
                <div class="section">
                    <h2 class="section-title">📋 Daftar Pengeluaran Operasional</h2>
                    <div class="table-container">
                        <table>
                            <thead>
                                <tr>
                                    <th>📅 Tanggal</th>
                                    <th>👤 User</th>
                                    <th>🏷️ Kategori</th>
                                    <th>📦 Barang/Jasa</th>
                                    <th>🔢 Jumlah</th>
                                    <th>💵 Harga</th>
                                    <th>💳 Bayar</th>
                                    <th>🏭 Supplier</th>
                                    <th>💰 Total</th>
                                    <th>📊 Akun & Status</th>
                                </tr>
                            </thead>
                            <tbody>
                                {transaction_rows}
                            </tbody>
                        </table>
                    </div>
                </div>
                
                <!-- Action Buttons -->
                <div class="section" style="text-align: center;">
                    <h2 class="section-title">⚡ Aksi Cepat</h2>
                    <div style="display: flex; gap: 15px; justify-content: center; flex-wrap: wrap;">
                        <a href="/penjualan" class="btn">🛍️ Input Penjualan</a>
                        <a href="/pembelian" class="btn">🛒 Input Pembelian</a>
                        <a href="/jurnal-umum" class="btn btn-secondary">📝 Lihat Jurnal</a>
                        <a href="/laporan-keuangan" class="btn btn-secondary">📊 Laporan Keuangan</a>
                    </div>
                </div>
            </div>
        </div>
    
    </body>
    </html>
    """
    return html

# ============================================================
# 🔹 ROUTE: Buku Besar Pembantu Utang 
# ============================================================
@app.route("/buku-besar-pembantu-utang")
def buku_besar_pembantu_utang():
    if not session.get('logged_in'):
        return redirect('/login')
    
    user_email = session.get('user_email')
    
    try:
        # Ambil data utang dari pembelian kredit dan pelunasan
        utang_data = get_utang_data()
        
        # Hitung total utang
        total_utang = sum(supplier['sisa_utang'] for supplier in utang_data.values())
        
        # Format currency helper
        def rp(amount):
            return f"Rp {amount:,.0f}".replace(",", ".")
        
        # Generate HTML untuk setiap supplier
        supplier_sections = ""
        for supplier_name, data in utang_data.items():
            supplier_sections += generate_supplier_section(supplier_name, data, rp)
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Buku Besar Pembantu Utang - PINKILANG</title>
            <meta charset="utf-8">
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}
                
                body {{
                    font-family: 'Arial', sans-serif;
                    background: linear-gradient(135deg, #fff0f5, #ffe6f2);
                    padding: 20px;
                    min-height: 100vh;
                }}
                
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 15px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                    overflow: hidden;
                }}
                
                .header {{
                    background: linear-gradient(135deg, #ff6666, #ff4d4d);
                    color: white;
                    padding: 25px;
                    text-align: center;
                }}
                
                .back-btn {{
                    display: inline-block;
                    padding: 10px 20px;
                    background: rgba(255,255,255,0.2);
                    color: white;
                    text-decoration: none;
                    border-radius: 8px;
                    margin-bottom: 15px;
                    border: 1px solid rgba(255,255,255,0.3);
                    font-size: 14px;
                }}
                
                .back-btn:hover {{
                    background: rgba(255,255,255,0.3);
                }}
                
                h1 {{
                    font-size: 28px;
                    margin-bottom: 10px;
                }}
                
                .content {{
                    padding: 25px;
                }}
                
                .summary-card {{
                    background: linear-gradient(135deg, #ff6666, #ff4d4d);
                    color: white;
                    padding: 20px;
                    border-radius: 10px;
                    text-align: center;
                    margin-bottom: 25px;
                    box-shadow: 0 4px 15px rgba(255,102,102,0.3);
                }}
                
                .summary-number {{
                    font-size: 32px;
                    font-weight: bold;
                    margin: 10px 0;
                }}
                
                .supplier-section {{
                    background: #f8f9fa;
                    border-radius: 10px;
                    padding: 20px;
                    margin-bottom: 20px;
                    border-left: 5px solid #ff6666;
                }}
                
                .supplier-header {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 15px;
                    padding-bottom: 10px;
                    border-bottom: 2px solid #e9ecef;
                }}
                
                .supplier-name {{
                    font-size: 20px;
                    font-weight: bold;
                    color: #333;
                }}
                
                .supplier-total {{
                    font-size: 18px;
                    font-weight: bold;
                    color: #ff6666;
                }}
                
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 10px;
                    background: white;
                    border-radius: 8px;
                    overflow: hidden;
                }}
                
                th, td {{
                    padding: 12px;
                    text-align: left;
                    border-bottom: 1px solid #dee2e6;
                }}
                
                th {{
                    background: #ff6666;
                    color: white;
                    font-weight: bold;
                }}
                
                tr:hover {{
                    background: #fff5f5;
                }}
                
                .debit {{
                    color: #009933;
                    font-weight: bold;
                }}
                
                .kredit {{
                    color: #cc0000;
                    font-weight: bold;
                }}
                
                .saldo {{
                    font-weight: bold;
                    color: #cc0000;
                }}
                
                .status-badge {{
                    padding: 4px 8px;
                    border-radius: 12px;
                    font-size: 12px;
                    font-weight: bold;
                    color: white;
                }}
                
                .status-lunas {{
                    background: #00cc66;
                }}
                
                .status-belum {{
                    background: #ff6666;
                }}
                
                .empty-state {{
                    text-align: center;
                    padding: 40px;
                    color: #999;
                    font-style: italic;
                }}
                
                .info-box {{
                    background: #ffe6e6;
                    border: 1px solid #ffb3b3;
                    border-radius: 8px;
                    padding: 15px;
                    margin: 15px 0;
                    color: #cc0000;
                }}
                
                .action-buttons {{
                    text-align: center;
                    margin-top: 20px;
                    padding-top: 20px;
                    border-top: 1px solid #eee;
                }}
                
                .btn {{
                    display: inline-block;
                    padding: 10px 20px;
                    margin: 0 5px;
                    background: #ff6666;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    font-size: 14px;
                }}
                
                .btn:hover {{
                    background: #ff4d4d;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <!-- Header -->
                <div class="header">
                    <a href="/dashboard" class="back-btn">← Kembali ke Dashboard</a>
                    <h1>📋 Buku Besar Pembantu Utang</h1>
                    <p>Sistem Terintegrasi dengan Pembelian Kredit - PINKILANG</p>
                </div>
                    
                    <!-- Summary Card -->
                    <div class="summary-card">
                        <div>💰 Total Utang Usaha</div>
                        <div class="summary-number">{rp(total_utang)}</div>
                        <div>{len(utang_data)} Supplier</div>
                    </div>
                    
                    <!-- Supplier Sections -->
                    {supplier_sections if utang_data else '''
                    <div class="empty-state">
                        📊 Tidak ada data utang
                        <br><br>
                        <a href="/pembelian" class="btn">🛒 Input Pembelian Kredit</a>
                    </div>
                    '''}
                    
                    <!-- Action Buttons -->
                    <div class="action-buttons">
                        <a href="/pembelian" class="btn">🛒 Ke Modul Pembelian</a>
                        <a href="/buku-besar" class="btn">📚 Ke Buku Besar</a>
                        <a href="/neraca-saldo-setelah-penyesuaian" class="btn">🏦 Ke Neraca Saldo Setelah Penyesuaian</a>
                        <button onclick="window.print()" class="btn">🖨️ Cetak Laporan</button>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        return html
        
    except Exception as e:
        logger.error(f"❌ Error di buku besar pembantu utang: {str(e)}")
        return f"Error: {str(e)}"

def get_utang_data():
    """Ambil data utang dari pembelian kredit dan pelunasan"""
    utang_data = {}
    
    try:
        # Ambil semua pembelian kredit
        pembelian_kredit = supabase.table("pembelian").select("*").eq("metode_pembayaran", "KREDIT").execute().data or []
        
        for pembelian in pembelian_kredit:
            supplier_name = pembelian.get('nama_supplier', 'Tidak Diketahui')
            
            if supplier_name not in utang_data:
                utang_data[supplier_name] = {
                    'transaksi': [],
                    'total_utang': 0,
                    'total_pelunasan': 0,
                    'sisa_utang': 0
                }
            
            # Ambil data pelunasan untuk pembelian ini
            pelunasan_result = supabase.table("pelunasan_utang").select("*").eq("pembelian_id", pembelian['id']).execute()
            pelunasan_data = pelunasan_result.data or []
            
            total_pelunasan = sum(p['jumlah_bayar'] for p in pelunasan_data)
            sisa_utang = pembelian['total_pembelian'] - total_pelunasan
            
            # Simpan transaksi utang
            transaksi_data = {
                'tanggal': pembelian['tanggal'],
                'keterangan': f"Pembelian {pembelian['nama_barang']}",
                'debit': 0,
                'kredit': pembelian['total_pembelian'],
                'saldo': pembelian['total_pembelian'],
                'type': 'UTANG'
            }
            utang_data[supplier_name]['transaksi'].append(transaksi_data)
            
            # Simpan pelunasan
            for pelunasan in pelunasan_data:
                pelunasan_transaksi = {
                    'tanggal': pelunasan['tanggal_bayar'],
                    'keterangan': f"Pelunasan utang",
                    'debit': pelunasan['jumlah_bayar'],
                    'kredit': 0,
                    'saldo': sisa_utang,
                    'type': 'PELUNASAN'
                }
                utang_data[supplier_name]['transaksi'].append(pelunasan_transaksi)
            
            # Update totals
            utang_data[supplier_name]['total_utang'] += pembelian['total_pembelian']
            utang_data[supplier_name]['total_pelunasan'] += total_pelunasan
            utang_data[supplier_name]['sisa_utang'] += sisa_utang
        
        # Sort transaksi by date untuk setiap supplier
        for supplier in utang_data.values():
            supplier['transaksi'] = sorted(supplier['transaksi'], key=lambda x: x['tanggal'])
            
            # Hitung saldo running (utang saldo normal kredit)
            saldo = 0
            for transaksi in supplier['transaksi']:
                saldo += transaksi['kredit'] - transaksi['debit']  # Utang bertambah di kredit, berkurang di debit
                transaksi['saldo'] = saldo
        
    except Exception as e:
        logger.error(f"❌ Error get_utang_data: {str(e)}")
    
    return utang_data

def generate_supplier_section(supplier_name, data, rp_func):
    """Generate HTML section untuk setiap supplier"""
    
    transaksi_rows = ""
    
    for i, transaksi in enumerate(data['transaksi']):
        status_badge = '<span class="status-badge status-lunas">LUNAS</span>' if transaksi['saldo'] == 0 else '<span class="status-badge status-belum">BELUM</span>'
        
        transaksi_rows += f"""
        <tr>
            <td>{datetime.strptime(transaksi['tanggal'], '%Y-%m-%d').strftime('%d/%m/%Y')}</td>
            <td>{transaksi['keterangan']}</td>
            <td class="debit">{rp_func(transaksi['debit']) if transaksi['debit'] > 0 else '-'}</td>
            <td class="kredit">{rp_func(transaksi['kredit']) if transaksi['kredit'] > 0 else '-'}</td>
            <td class="saldo">{rp_func(transaksi['saldo'])}</td>
            <td>{status_badge}</td>
        </tr>
        """
    
    return f"""
    <div class="supplier-section">
        <div class="supplier-header">
            <div class="supplier-name">🏭 {supplier_name}</div>
            <div class="supplier-total">Sisa: {rp_func(data['sisa_utang'])}</div>
        </div>
        
        <table>
            <thead>
                <tr>
                    <th>Tanggal</th>
                    <th>Keterangan</th>
                    <th>Debit (Pelunasan)</th>
                    <th>Kredit (Utang)</th>
                    <th>Saldo</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                {transaksi_rows}
                <tr style="background: #f8f9fa; font-weight: bold;">
                    <td colspan="2">TOTAL</td>
                    <td class="debit">{rp_func(data['total_pelunasan'])}</td>
                    <td class="kredit">{rp_func(data['total_utang'])}</td>
                    <td class="saldo">{rp_func(data['sisa_utang'])}</td>
                    <td>{'<span class="status-badge status-lunas">LUNAS</span>' if data['sisa_utang'] == 0 else '<span class="status-badge status-belum">BELUM LUNAS</span>'}</td>
                </tr>
            </tbody>
        </table>
    </div>
    """

# ============================================================
# 🔹 ROUTE: Buku Besar Pembantu Piutang 
# ============================================================
@app.route("/buku-besar-pembantu-piutang")
def buku_besar_pembantu_piutang():
    if not session.get('logged_in'):
        return redirect('/login')
    
    user_email = session.get('user_email')
    
    try:
        # Ambil data piutang dari penjualan kredit dan pelunasan
        piutang_data = get_piutang_data()
        
        # Hitung total piutang
        total_piutang = sum(customer['sisa_piutang'] for customer in piutang_data.values())
        
        # Format currency helper
        def rp(amount):
            return f"Rp {amount:,.0f}".replace(",", ".")
        
        # Generate HTML untuk setiap pelanggan
        customer_sections = ""
        for customer_name, data in piutang_data.items():
            customer_sections += generate_customer_section(customer_name, data, rp)
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Buku Besar Pembantu Piutang - PINKILANG</title>
            <meta charset="utf-8">
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}
                
                body {{
                    font-family: 'Arial', sans-serif;
                    background: linear-gradient(135deg, #ffe6f2, #fff0f7);
                    padding: 20px;
                    min-height: 100vh;
                }}
                
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 15px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                    overflow: hidden;
                }}
                
                .header {{
                    background: linear-gradient(135deg, #ff85b3, #ff66a3);
                    color: white;
                    padding: 25px;
                    text-align: center;
                }}
                
                .back-btn {{
                    display: inline-block;
                    padding: 10px 20px;
                    background: rgba(255,255,255,0.2);
                    color: white;
                    text-decoration: none;
                    border-radius: 8px;
                    margin-bottom: 15px;
                    border: 1px solid rgba(255,255,255,0.3);
                    font-size: 14px;
                }}
                
                .back-btn:hover {{
                    background: rgba(255,255,255,0.3);
                }}
                
                h1 {{
                    font-size: 28px;
                    margin-bottom: 10px;
                }}
                
                .content {{
                    padding: 25px;
                }}
                
                .summary-card {{
                    background: linear-gradient(135deg, #66b3ff, #4d94ff);
                    color: white;
                    padding: 20px;
                    border-radius: 10px;
                    text-align: center;
                    margin-bottom: 25px;
                    box-shadow: 0 4px 15px rgba(102,179,255,0.3);
                }}
                
                .summary-number {{
                    font-size: 32px;
                    font-weight: bold;
                    margin: 10px 0;
                }}
                
                .customer-section {{
                    background: #f8f9fa;
                    border-radius: 10px;
                    padding: 20px;
                    margin-bottom: 20px;
                    border-left: 5px solid #66b3ff;
                }}
                
                .customer-header {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 15px;
                    padding-bottom: 10px;
                    border-bottom: 2px solid #e9ecef;
                }}
                
                .customer-name {{
                    font-size: 20px;
                    font-weight: bold;
                    color: #333;
                }}
                
                .customer-total {{
                    font-size: 18px;
                    font-weight: bold;
                    color: #ff6666;
                }}
                
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 10px;
                    background: white;
                    border-radius: 8px;
                    overflow: hidden;
                }}
                
                th, td {{
                    padding: 12px;
                    text-align: left;
                    border-bottom: 1px solid #dee2e6;
                }}
                
                th {{
                    background: #ff85b3;
                    color: white;
                    font-weight: bold;
                }}
                
                tr:hover {{
                    background: #fff5f9;
                }}
                
                .debit {{
                    color: #009933;
                    font-weight: bold;
                }}
                
                .kredit {{
                    color: #cc0000;
                    font-weight: bold;
                }}
                
                .saldo {{
                    font-weight: bold;
                    color: #0066cc;
                }}
                
                .status-badge {{
                    padding: 4px 8px;
                    border-radius: 12px;
                    font-size: 12px;
                    font-weight: bold;
                    color: white;
                }}
                
                .status-lunas {{
                    background: #00cc66;
                }}
                
                .status-belum {{
                    background: #ff6666;
                }}
                
                .empty-state {{
                    text-align: center;
                    padding: 40px;
                    color: #999;
                    font-style: italic;
                }}
                
                .info-box {{
                    background: #e6f7ff;
                    border: 1px solid #91d5ff;
                    border-radius: 8px;
                    padding: 15px;
                    margin: 15px 0;
                    color: #1890ff;
                }}
                
                .action-buttons {{
                    text-align: center;
                    margin-top: 20px;
                    padding-top: 20px;
                    border-top: 1px solid #eee;
                }}
                
                .btn {{
                    display: inline-block;
                    padding: 10px 20px;
                    margin: 0 5px;
                    background: #ff66a3;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    font-size: 14px;
                }}
                
                .btn:hover {{
                    background: #ff4d94;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <!-- Header -->
                <div class="header">
                    <a href="/dashboard" class="back-btn">← Kembali ke Dashboard</a>
                    <h1>📋 Buku Besar Pembantu Piutang</h1>
                    <p>Sistem Terintegrasi dengan Penjualan Kredit - PINKILANG</p>
                </div>
                    
                    <!-- Summary Card -->
                    <div class="summary-card">
                        <div>💰 Total Piutang Usaha</div>
                        <div class="summary-number">{rp(total_piutang)}</div>
                        <div>{len(piutang_data)} Pelanggan</div>
                    </div>
                    
                    <!-- Customer Sections -->
                    {customer_sections if piutang_data else '''
                    <div class="empty-state">
                        📊 Tidak ada data piutang
                        <br><br>
                        <a href="/penjualan" class="btn">🛍️ Input Penjualan Kredit</a>
                    </div>
                    '''}
                    
                    <!-- Action Buttons -->
                    <div class="action-buttons">
                        <a href="/penjualan" class="btn">🛍️ Ke Modul Penjualan</a>
                        <a href="/buku-besar" class="btn">📚 Ke Buku Besar</a>
                        <a href="/neraca-saldo-setelah-penyesuaian" class="btn">🏦 Ke Neraca Saldo Setelah Penyesuaian</a>
                        <button onclick="window.print()" class="btn">🖨️ Cetak Laporan</button>
                    </div>
                </div>
            </div>
            
        </body>
        </html>
        """
        return html
        
    except Exception as e:
        logger.error(f"❌ Error di buku besar pembantu piutang: {str(e)}")
        return f"Error: {str(e)}"

def get_piutang_data():
    """Ambil data piutang dari penjualan kredit dan pelunasan"""
    piutang_data = {}
    
    try:
        # Ambil semua penjualan kredit
        penjualan_kredit = supabase.table("penjualan").select("*").eq("metode_pembayaran", "KREDIT").execute().data or []
        
        for penjualan in penjualan_kredit:
            customer_name = penjualan.get('nama_pelanggan', 'Tidak Diketahui')
            
            if customer_name not in piutang_data:
                piutang_data[customer_name] = {
                    'transaksi': [],
                    'total_piutang': 0,
                    'total_pelunasan': 0,
                    'sisa_piutang': 0
                }
            
            # Ambil data pelunasan untuk penjualan ini
            pelunasan_result = supabase.table("pelunasan_piutang").select("*").eq("penjualan_id", penjualan['id']).execute()
            pelunasan_data = pelunasan_result.data or []
            
            total_pelunasan = sum(p['jumlah_bayar'] for p in pelunasan_data)
            sisa_piutang = penjualan['total_penjualan'] - total_pelunasan
            
            # Simpan transaksi
            transaksi_data = {
                'tanggal': penjualan['tanggal'],
                'keterangan': f"Penjualan {penjualan['nama_barang']}",
                'debit': penjualan['total_penjualan'],
                'kredit': 0,
                'saldo': penjualan['total_penjualan'],
                'type': 'PIUTANG'
            }
            piutang_data[customer_name]['transaksi'].append(transaksi_data)
            
            # Simpan pelunasan
            for pelunasan in pelunasan_data:
                pelunasan_transaksi = {
                    'tanggal': pelunasan['tanggal_bayar'],
                    'keterangan': f"Pelunasan piutang",
                    'debit': 0,
                    'kredit': pelunasan['jumlah_bayar'],
                    'saldo': sisa_piutang,
                    'type': 'PELUNASAN'
                }
                piutang_data[customer_name]['transaksi'].append(pelunasan_transaksi)
            
            # Update totals
            piutang_data[customer_name]['total_piutang'] += penjualan['total_penjualan']
            piutang_data[customer_name]['total_pelunasan'] += total_pelunasan
            piutang_data[customer_name]['sisa_piutang'] += sisa_piutang
        
        # Sort transaksi by date untuk setiap customer
        for customer in piutang_data.values():
            customer['transaksi'] = sorted(customer['transaksi'], key=lambda x: x['tanggal'])
            
            # Hitung saldo running
            saldo = 0
            for transaksi in customer['transaksi']:
                saldo += transaksi['debit'] - transaksi['kredit']
                transaksi['saldo'] = saldo
        
    except Exception as e:
        logger.error(f"❌ Error get_piutang_data: {str(e)}")
    
    return piutang_data

def generate_customer_section(customer_name, data, rp_func):
    """Generate HTML section untuk setiap customer"""
    
    transaksi_rows = ""
    saldo_awal = 0
    
    for i, transaksi in enumerate(data['transaksi']):
        status_badge = '<span class="status-badge status-lunas">LUNAS</span>' if transaksi['saldo'] == 0 else '<span class="status-badge status-belum">BELUM</span>'
        
        transaksi_rows += f"""
        <tr>
            <td>{datetime.strptime(transaksi['tanggal'], '%Y-%m-%d').strftime('%d/%m/%Y')}</td>
            <td>{transaksi['keterangan']}</td>
            <td class="debit">{rp_func(transaksi['debit']) if transaksi['debit'] > 0 else '-'}</td>
            <td class="kredit">{rp_func(transaksi['kredit']) if transaksi['kredit'] > 0 else '-'}</td>
            <td class="saldo">{rp_func(transaksi['saldo'])}</td>
            <td>{status_badge}</td>
        </tr>
        """
    
    return f"""
    <div class="customer-section">
        <div class="customer-header">
            <div class="customer-name">👤 {customer_name}</div>
            <div class="customer-total">Sisa: {rp_func(data['sisa_piutang'])}</div>
        </div>
        
        <table>
            <thead>
                <tr>
                    <th>Tanggal</th>
                    <th>Keterangan</th>
                    <th>Debit (Piutang)</th>
                    <th>Kredit (Pelunasan)</th>
                    <th>Saldo</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                {transaksi_rows}
                <tr style="background: #f8f9fa; font-weight: bold;">
                    <td colspan="2">TOTAL</td>
                    <td class="debit">{rp_func(data['total_piutang'])}</td>
                    <td class="kredit">{rp_func(data['total_pelunasan'])}</td>
                    <td class="saldo">{rp_func(data['sisa_piutang'])}</td>
                    <td>{'<span class="status-badge status-lunas">LUNAS</span>' if data['sisa_piutang'] == 0 else '<span class="status-badge status-belum">BELUM LUNAS</span>'}</td>
                </tr>
            </tbody>
        </table>
    </div>
    """

# ============================================================
# 🔹 ROUTE: Laporan Laba Rugi (TERINTEGRASI NERACA LAJUR & NSSP) DENGAN HPP DETAIL
# ============================================================
@app.route("/laba-rugi")
def laba_rugi():
    if not session.get('logged_in'):
        return redirect('/login')
    
    user_email = session.get('user_email')
    
    try:
        # Ambil data dari neraca lajur untuk perhitungan laba rugi
        neraca_lajur_data = get_neraca_lajur_simple()
        
        if not neraca_lajur_data or 'akun_data' not in neraca_lajur_data:
            return create_error_page("Laba Rugi", "Tidak dapat mengambil data neraca lajur. Pastikan neraca lajur sudah dibuat terlebih dahulu.")
        
        akun_data = neraca_lajur_data['akun_data']
        neraca_data = hitung_laba_rugi_terintegrasi(akun_data)
        
        if not neraca_data:
            return create_error_page("Laba Rugi", "Tidak dapat menghitung data laba rugi dari data akun yang tersedia.")
        
        # Format currency helper
        def rp(amount):
            try:
                return f"Rp {int(amount):,}".replace(",", ".")
            except:
                return "Rp 0"
        
        # Generate HTML sections
        pendapatan_section = generate_pendapatan_section(neraca_data, rp)
        hpp_section = generate_hpp_section(neraca_data, rp)  # ✅ SECTION HPP BARU
        laba_kotor_section = generate_laba_kotor_section(neraca_data, rp)  # ✅ SECTION LABA KOTOR
        beban_section = generate_beban_section(neraca_data, rp)
        perhitungan_section = generate_perhitungan_section(neraca_data, rp)
        breakdown_section = generate_breakdown_section(neraca_data, rp)
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Laporan Laba Rugi - PINKILANG</title>
    <meta charset="utf-8">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Arial', sans-serif;
            background: linear-gradient(135deg, #ffe6f2, #fff0f7);
            padding: 20px;
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #ff66a3, #ff4d94);
            color: white;
            padding: 25px;
            text-align: center;
        }}
        
        .back-btn {{
            display: inline-block;
            padding: 10px 20px;
            background: rgba(255,255,255,0.2);
            color: white;
            text-decoration: none;
            border-radius: 8px;
            margin-bottom: 15px;
            border: 1px solid rgba(255,255,255,0.3);
        }}
        
        .back-btn:hover {{
            background: rgba(255,255,255,0.3);
        }}
        
        h1 {{
            font-size: 28px;
            margin-bottom: 10px;
        }}
        
        .content {{
            padding: 25px;
        }}
        
        .section {{
            margin: 25px 0;
            padding: 20px;
            background: #fff5f9;
            border-radius: 12px;
            border-left: 5px solid #ff66a3;
        }}
        
        .section-title {{
            color: #ff66a3;
            font-size: 22px;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #ffe6f2;
        }}
        
        .calculation-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 4px 15px rgba(255,102,163,0.1);
        }}
        
        .calculation-table th {{
            background: #ff66a3;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: bold;
        }}
        
        .calculation-table td {{
            padding: 12px;
            border-bottom: 1px solid #ffe6f2;
        }}
        
        .calculation-table tr:hover {{
            background: #fff5f9;
        }}
        
        .number {{
            text-align: right;
            font-family: 'Courier New', monospace;
            font-weight: bold;
        }}
        
        .positive {{
            color: #00cc66;
        }}
        
        .negative {{
            color: #ff6666;
        }}
        
        .total-row {{
            background: #ffe6f2;
            font-weight: bold;
            font-size: 16px;
        }}
        
        .subtotal-row {{
            background: #f8f9fa;
            font-weight: bold;
        }}
        
        .info-box {{
            background: #e6f7ff;
            border: 1px solid #91d5ff;
            border-radius: 8px;
            padding: 15px;
            margin: 15px 0;
            color: #0066cc;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 4px 15px rgba(255,102,163,0.1);
            border: 1px solid #ffe6f2;
        }}
        
        .stat-number {{
            font-size: 24px;
            font-weight: bold;
            color: #ff66a3;
            margin: 10px 0;
        }}
        
        .stat-label {{
            color: #e83e8c;
            font-size: 14px;
            font-weight: bold;
        }}
        
        .breakdown-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin: 20px 0;
        }}
        
        .breakdown-item {{
            background: white;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #ff66a3;
        }}
        
        .breakdown-header {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 10px;
            font-weight: bold;
        }}
        
        .progress-bar {{
            background: #e6f2ff;
            border-radius: 10px;
            height: 10px;
            margin: 5px 0;
        }}
        
        .progress-fill {{
            background: #66b3ff;
            height: 100%;
            border-radius: 10px;
        }}
        
        .btn {{
            display: inline-block;
            padding: 10px 20px;
            background: #ff66a3;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            margin: 5px;
        }}
        
        .btn:hover {{
            background: #ff4d94;
        }}
        
        .period-selector {{
            background: white;
            padding: 15px;
            border-radius: 8px;
            margin: 15px 0;
            text-align: center;
        }}
        
        .empty-state {{
            text-align: center;
            padding: 40px;
            color: #999;
            font-style: italic;
        }}

        .hpp-formula {{
            background: #fff0f0;
            padding: 10px 15px;
            border-radius: 5px;
            margin: 10px 0;
            border-left: 3px solid #ff6666;
        }}

        .laba-kotor-box {{
            background: #f0fff0;
            padding: 15px;
            border-radius: 8px;
            margin: 15px 0;
            border: 2px solid #00cc66;
            text-align: center;
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <a href="/dashboard" class="back-btn">← Kembali ke Dashboard</a>
            <h1>📊 Laporan Laba Rugi</h1>
            <p>Terintegrasi dengan Neraca Lajur & NSSP - PINKILANG</p>
        </div>
        
        <div class="content">
            <!-- Section Pendapatan -->
            {pendapatan_section}
            
            <!-- Section HPP Detail -->
            {hpp_section}
            
            <!-- Section Laba Kotor -->
            {laba_kotor_section}
            
            <!-- Section Beban -->
            {beban_section}
            
            <!-- Section Perhitungan Laba Rugi -->
            {perhitungan_section}
            
            <!-- Section Breakdown -->
            {breakdown_section}
            
            <!-- Action Buttons -->
            <div style="text-align: center; margin-top: 30px;">
                <a href="/neraca-lajur" class="btn">📊 Lihat Neraca Lajur</a>
                <a href="/neraca-saldo-setelah-penyesuaian" class="btn">🏦 Lihat NSSP</a>
                <a href="/laporan-perubahan-modal" class="btn">👨‍💼 Lihat Perubahan Modal</a>
                <button onclick="window.print()" class="btn">🖨️ Cetak Laporan</button>
            </div>
        </div>
    </div>
    
    <script>
        // Print functionality
        function printReport() {{
            window.print();
        }}
    </script>
</body>
</html>
"""
        return html 
        
    except Exception as e:
        logger.error(f"❌ Error di laporan laba rugi: {str(e)}")
        return create_error_page("Laba Rugi", str(e))

def hitung_laba_rugi_terintegrasi(akun_data):
    """
    Menghitung laba rugi berdasarkan list akun yang diberikan
    DENGAN PERHITUNGAN HPP YANG SESUAI FORMAT CONTOH
    """
    try:
        logger.info("🧮 Memulai perhitungan laba rugi terintegrasi dengan HPP...")
        
        # Inisialisasi variabel
        pendapatan_penjualan = 0
        pendapatan_lainnya = 0
        
        # VARIABEL HPP - sesuai format dari contoh
        persediaan_awal = 0
        pembelian = 0
        persediaan_akhir = 0
        hpp = 0
        
        beban_operasional = {}
        beban_non_operasional = {}
        
        # Identifikasi akun-akun HPP dan lainnya
        for akun_nama, data in akun_data.items():
            akun_lower = akun_nama.lower()
            
            # Gunakan kolom NSSP untuk laba rugi
            nssp_debit = data.get('nssp_debit', 0) or 0
            nssp_kredit = data.get('nssp_kredit', 0) or 0
            
            # PENDAPATAN (Akun Nomor 4xxx)
            if any(keyword in akun_lower for keyword in ['pendapatan', 'penjualan', 'revenue', 'income']) or \
               str(data.get('kode', '')).startswith('4'):
                if nssp_kredit > nssp_debit:
                    if 'penjualan' in akun_lower:
                        pendapatan_penjualan += (nssp_kredit - nssp_debit)
                    else:
                        pendapatan_lainnya += (nssp_kredit - nssp_debit)
            
            # KOMPONEN HPP - DETECT OTOMATIS
            # Persediaan Awal
            elif any(keyword in akun_lower for keyword in ['persediaan awal', 'barang dagangan awal', 'persediaan dagang awal']):
                persediaan_awal = nssp_debit
                logger.info(f"📦 Persediaan Awal terdeteksi: {akun_nama} = {persediaan_awal}")
            
            # Pembelian
            elif any(keyword in akun_lower for keyword in ['pembelian', 'pembelian barang', 'beli barang']):
                pembelian = nssp_debit
                logger.info(f"🛒 Pembelian terdeteksi: {akun_nama} = {pembelian}")
            
            # Persediaan Akhir
            elif any(keyword in akun_lower for keyword in ['persediaan akhir', 'persediaan barang dagang akhir', 'persediaan dagang akhir']):
                persediaan_akhir = nssp_debit
                logger.info(f"📦 Persediaan Akhir terdeteksi: {akun_nama} = {persediaan_akhir}")
            
            # BEBAN (Akun Nomor 6xxx)
            elif any(keyword in akun_lower for keyword in ['beban', 'biaya']) or \
                 str(data.get('kode', '')).startswith('6'):
                if nssp_debit > 0:
                    # 1. Beban Listrik, Air dan Telepon (hanya yang namanya persis)
                    if 'beban listrik, air dan telepon' in akun_lower:
                        beban_operasional['Beban Listrik, Air dan Telepon'] = nssp_debit
                        logger.info(f"🔌 Beban Listrik, Air dan Telepon: {nssp_debit}")
                    
                    # 2. Beban Perlengkapan (hanya yang namanya persis)  
                    elif 'beban perlengkapan' in akun_lower:
                        beban_operasional['Beban Perlengkapan'] = nssp_debit
                        logger.info(f"📝 Beban Perlengkapan: {nssp_debit}")
                    
                    # 3. Semua beban lainnya masuk ke non-operasional
                    else:
                        beban_non_operasional[akun_nama] = nssp_debit
                        logger.info(f"📦 Beban Non-Operasional: {akun_nama} = {nssp_debit}")
        
        # 🎯 PERHITUNGAN HPP SESUAI FORMAT CONTOH
        # Rumus: HPP = (Persediaan Awal + Pembelian) - Persediaan Akhir
        if persediaan_awal > 0 or pembelian > 0:
            hpp = (persediaan_awal + pembelian) - persediaan_akhir
            logger.info(f"🧮 Perhitungan HPP: ({persediaan_awal} + {pembelian}) - {persediaan_akhir} = {hpp}")
        else:
            # Fallback ke metode lama jika tidak ada komponen HPP terpisah
            for akun_nama, data in akun_data.items():
                akun_lower = akun_nama.lower()
                nssp_debit = data.get('nssp_debit', 0) or 0
                if any(keyword in akun_lower for keyword in ['hpp', 'harga pokok', 'beban pokok', 'cost of goods']):
                    hpp += nssp_debit
            logger.info(f"🧮 HPP Fallback: {hpp}")

        # Hitung total
        total_pendapatan = pendapatan_penjualan + pendapatan_lainnya
        total_beban_operasional = sum(beban_operasional.values())
        total_beban_non_operasional = sum(beban_non_operasional.values())
        total_beban = hpp + total_beban_operasional + total_beban_non_operasional
        
        # Hitung laba kotor dan laba bersih
        laba_kotor = total_pendapatan - hpp
        laba_bersih = laba_kotor - total_beban_operasional - total_beban_non_operasional
        margin_laba = (laba_bersih / total_pendapatan * 100) if total_pendapatan > 0 else 0
        
        # Struktur hasil DENGAN KOMPONEN HPP DETAIL
        result = {
            'pendapatan': {
                'Pendapatan Penjualan': pendapatan_penjualan,
                'Pendapatan Lainnya': pendapatan_lainnya
            },
            'total_pendapatan': total_pendapatan,
            'hpp_detail': {
                'persediaan_awal': persediaan_awal,
                'pembelian': pembelian,
                'persediaan_akhir': persediaan_akhir,
                'hpp': hpp
            },
            'hpp': hpp,
            'laba_kotor': laba_kotor,
            'beban_operasional': beban_operasional,
            'total_beban_operasional': total_beban_operasional,
            'beban_non_operasional': beban_non_operasional,
            'total_beban_non_operasional': total_beban_non_operasional,
            'total_beban': total_beban,
            'laba_bersih': laba_bersih,
            'margin_laba': margin_laba
        }
        
        # Log hasil
        logger.info(f"📊 HASIL LABA RUGI DENGAN HPP:")
        logger.info(f"   Persediaan Awal: {persediaan_awal}")
        logger.info(f"   Pembelian: {pembelian}")
        logger.info(f"   Persediaan Akhir: {persediaan_akhir}")
        logger.info(f"   HPP: {hpp}")
        logger.info(f"   Total Pendapatan: {total_pendapatan}")
        logger.info(f"   Laba Kotor: {laba_kotor}")
        logger.info(f"   Beban Operasional: {total_beban_operasional}")
        logger.info(f"   Beban Non-Operasional: {total_beban_non_operasional}")
        logger.info(f"   Laba Bersih: {laba_bersih}")
        logger.info(f"   Margin Laba: {margin_laba:.2f}%")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Error hitung laba rugi terintegrasi: {str(e)}")
        import traceback
        logger.error(f"🔍 Traceback: {traceback.format_exc()}")
        return None

def generate_pendapatan_section(neraca_data, rp_func):
    """Generate HTML section untuk pendapatan"""
    pendapatan_items = ""
    for nama, jumlah in neraca_data['pendapatan'].items():
        if jumlah > 0:  # Hanya tampilkan yang memiliki nilai
            pendapatan_items += f"""
            <tr>
                <td>{nama}</td>
                <td class="number positive">+ {rp_func(jumlah)}</td>
            </tr>
            """
    
    return f"""
    <div class="section">
        <h2 class="section-title">💰 Pendapatan</h2>
        <table class="calculation-table">
            <thead>
                <tr>
                    <th>Jenis Pendapatan</th>
                    <th>Jumlah</th>
                </tr>
            </thead>
            <tbody>
                {pendapatan_items if pendapatan_items else '''
                <tr>
                    <td colspan="2" class="empty-state">
                        📊 Belum ada data pendapatan
                    </td>
                </tr>
                '''}
                <tr class="total-row">
                    <td><strong>TOTAL PENDAPATAN</strong></td>
                    <td class="number positive"><strong>+ {rp_func(neraca_data['total_pendapatan'])}</strong></td>
                </tr>
            </tbody>
        </table>
    </div>
    """

def generate_hpp_section(neraca_data, rp_func):
    """Generate HTML section untuk HPP detail seperti contoh"""
    
    hpp_detail = neraca_data.get('hpp_detail', {})
    persediaan_awal = hpp_detail.get('persediaan_awal', 0)
    pembelian = hpp_detail.get('pembelian', 0)
    persediaan_akhir = hpp_detail.get('persediaan_akhir', 0)
    hpp = hpp_detail.get('hpp', 0)
    
    # Hanya tampilkan section HPP jika ada data yang relevan
    if persediaan_awal > 0 or pembelian > 0:
        return f"""
        <div class="section">
            <h2 class="section-title">📦 Harga Pokok Penjualan (HPP)</h2>
            
            <div style="background: #fff; padding: 20px; border-radius: 8px; margin: 15px 0;">
                <h3 style="color: #ff66a3; margin-bottom: 15px;">Perhitungan HPP</h3>
                
                <table class="calculation-table">
                    <tbody>
                        <tr>
                            <td><strong>Persediaan Awal</strong></td>
                            <td class="number">{rp_func(persediaan_awal)}</td>
                        </tr>
                        <tr>
                            <td><strong>Pembelian</strong></td>
                            <td class="number">+ {rp_func(pembelian)}</td>
                        </tr>
                        <tr style="background: #f8f9fa;">
                            <td><strong>Barang Tersedia Untuk Dijual</strong></td>
                            <td class="number"><strong>{rp_func(persediaan_awal + pembelian)}</strong></td>
                        </tr>
                        <tr>
                            <td><strong>Persediaan Barang Dagang Akhir</strong></td>
                            <td class="number">- {rp_func(persediaan_akhir)}</td>
                        </tr>
                        <tr class="total-row">
                            <td><strong>HARGA POKOK PENJUALAN (HPP)</strong></td>
                            <td class="number negative"><strong>- {rp_func(hpp)}</strong></td>
                        </tr>
                    </tbody>
                </table>
                
                <div class="hpp-formula">
                    <p style="margin: 0; color: #666; font-size: 14px;">
                        <strong>📝 Rumus HPP:</strong> HPP = (Persediaan Awal + Pembelian) - Persediaan Akhir
                    </p>
                    <p style="margin: 5px 0 0 0; color: #666; font-size: 14px;">
                        <strong>🔍 Perhitungan:</strong> ({rp_func(persediaan_awal)} + {rp_func(pembelian)}) - {rp_func(persediaan_akhir)} = {rp_func(hpp)}
                    </p>
                </div>
            </div>
        </div>
        """
    else:
        # Fallback ke tampilan HPP sederhana
        return f"""
        <div class="section">
            <h2 class="section-title">📦 Harga Pokok Penjualan (HPP)</h2>
            <table class="calculation-table">
                <tbody>
                    <tr class="total-row">
                        <td><strong>HARGA POKOK PENJUALAN (HPP)</strong></td>
                        <td class="number negative"><strong>- {rp_func(neraca_data['hpp'])}</strong></td>
                    </tr>
                </tbody>
            </table>
        </div>
        """

def generate_laba_kotor_section(neraca_data, rp_func):
    """Generate HTML section untuk Laba Kotor"""
    
    return f"""
    <div class="section" style="background: #f0fff0; border-left: 5px solid #00cc66;">
        <h2 class="section-title" style="color: #00cc66;">📈 Laba Kotor</h2>
        
        <div class="laba-kotor-box">
            <h3 style="color: #006600; margin-bottom: 10px;">Laba Kotor</h3>
            <div style="font-size: 24px; font-weight: bold; color: #00cc66;">
                {rp_func(neraca_data['laba_kotor'])}
            </div>
            <p style="color: #006600; margin-top: 10px;">
                Total Pendapatan - HPP = {rp_func(neraca_data['total_pendapatan'])} - {rp_func(neraca_data['hpp'])}
            </p>
        </div>
        
        <table class="calculation-table">
            <tbody>
                <tr>
                    <td><strong>Total Pendapatan</strong></td>
                    <td class="number positive">+ {rp_func(neraca_data['total_pendapatan'])}</td>
                </tr>
                <tr>
                    <td><strong>Harga Pokok Penjualan (HPP)</strong></td>
                    <td class="number negative">- {rp_func(neraca_data['hpp'])}</td>
                </tr>
                <tr class="total-row" style="background: #e6ffe6;">
                    <td><strong>LABA KOTOR</strong></td>
                    <td class="number positive"><strong>{rp_func(neraca_data['laba_kotor'])}</strong></td>
                </tr>
            </tbody>
        </table>
    </div>
    """

def generate_beban_section(neraca_data, rp_func):
    """Generate HTML section untuk beban - TANPA HPP KARENA SUDAH ADA SECTION TERPISAH"""
    
    # Beban Operasional
    beban_operasional_items = ""
    for nama, jumlah in neraca_data['beban_operasional'].items():
        beban_operasional_items += f"""
        <tr>
            <td style="padding-left: 20px;">{nama}</td>
            <td class="number negative">- {rp_func(jumlah)}</td>
        </tr>
        """
    
    beban_operasional_section = ""
    if beban_operasional_items:
        beban_operasional_section = f"""
        <tr class="subtotal-row">
            <td><strong>Beban Operasional</strong></td>
            <td></td>
        </tr>
        {beban_operasional_items}
        <tr>
            <td style="padding-left: 20px;"><em>Total Beban Operasional</em></td>
            <td class="number negative"><strong>- {rp_func(neraca_data['total_beban_operasional'])}</strong></td>
        </tr>
        """
    
    # Beban Non-Operasional
    beban_non_operasional_items = ""
    for nama, jumlah in neraca_data['beban_non_operasional'].items():
        beban_non_operasional_items += f"""
        <tr>
            <td style="padding-left: 20px;">{nama}</td>
            <td class="number negative">- {rp_func(jumlah)}</td>
        </tr>
        """
    
    beban_non_operasional_section = ""
    if beban_non_operasional_items:
        beban_non_operasional_section = f"""
        <tr class="subtotal-row">
            <td><strong>Beban Lainnya</strong></td>
            <td></td>
        </tr>
        {beban_non_operasional_items}
        <tr>
            <td style="padding-left: 20px;"><em>Total Beban Lainnya</em></td>
            <td class="number negative"><strong>- {rp_func(neraca_data['total_beban_non_operasional'])}</strong></td>
        </tr>
        """
    
    return f"""
    <div class="section">
        <h2 class="section-title">📉 Beban dan Biaya</h2>
        <table class="calculation-table">
            <thead>
                <tr>
                    <th>Jenis Beban</th>
                    <th>Jumlah</th>
                </tr>
            </thead>
            <tbody>
                {beban_operasional_section}
                {beban_non_operasional_section}
                {'''
                <tr>
                    <td colspan="2" class="empty-state">
                        📊 Belum ada data beban operasional dan lainnya
                    </td>
                </tr>
                ''' if not any([neraca_data['beban_operasional'], neraca_data['beban_non_operasional']]) else ''}
                <tr class="total-row">
                    <td><strong>TOTAL BEBAN OPERASIONAL & LAINNYA</strong></td>
                    <td class="number negative"><strong>- {rp_func(neraca_data['total_beban_operasional'] + neraca_data['total_beban_non_operasional'])}</strong></td>
                </tr>
            </tbody>
        </table>
    </div>
    """

def generate_perhitungan_section(neraca_data, rp_func):
    """Generate HTML section untuk perhitungan laba rugi"""
    is_laba = neraca_data['laba_bersih'] >= 0
    
    return f"""
    <div class="section" style="background: {'#f0fff0' if is_laba else '#fff0f0'}; border-left: 5px solid {'#00cc66' if is_laba else '#ff6666'};">
        <h2 class="section-title" style="color: {'#00cc66' if is_laba else '#ff6666'};">
            {'💰 Laba Bersih' if is_laba else '📉 Rugi Bersih'}
        </h2>
        
        <table class="calculation-table">
            <tbody>
                <tr>
                    <td><strong>Laba Kotor</strong></td>
                    <td class="number positive"><strong>+ {rp_func(neraca_data['laba_kotor'])}</strong></td>
                </tr>
                <tr>
                    <td><strong>Total Beban Operasional & Lainnya</strong></td>
                    <td class="number negative"><strong>- {rp_func(neraca_data['total_beban_operasional'] + neraca_data['total_beban_non_operasional'])}</strong></td>
                </tr>
                <tr class="total-row" style="background: {'#e6ffe6' if is_laba else '#ffe6e6'};">
                    <td><strong>{'LABA BERSIH' if is_laba else 'RUGI BERSIH'}</strong></td>
                    <td class="number {'positive' if is_laba else 'negative'}">
                        <strong>{rp_func(abs(neraca_data['laba_bersih']))}</strong>
                    </td>
                </tr>
                <tr>
                    <td><strong>Margin { 'Laba' if is_laba else 'Rugi' }</strong></td>
                    <td class="number {'positive' if is_laba else 'negative'}">
                        <strong>{neraca_data['margin_laba']:.1f}%</strong>
                    </td>
                </tr>
            </tbody>
        </table>
        
        <div style="text-align: center; margin-top: 15px; padding: 15px; background: {'#d4ffd4' if is_laba else '#ffd4d4'}; border-radius: 8px;">
            <h3 style="color: {'#006600' if is_laba else '#cc0000'};">
                {'🎉 PERUSAHAAN UNTUNG' if is_laba else '⚠️ PERUSAHAAN RUGI'}
            </h3>
            <p style="color: {'#006600' if is_laba else '#cc0000'}; margin: 5px 0;">
                {f"Setiap Rp 100 pendapatan menghasilkan Rp {neraca_data['margin_laba']:.1f} laba" if is_laba else f"Setiap Rp 100 pendapatan mengalami Rp {abs(neraca_data['margin_laba']):.1f} rugi"}
            </p>
        </div>
    </div>
    """

def generate_breakdown_section(neraca_data, rp_func):
    """Generate HTML section untuk breakdown"""
    
    # Hitung persentase
    total_pendapatan = neraca_data['total_pendapatan'] if neraca_data['total_pendapatan'] > 0 else 1
    hpp_percentage = (neraca_data['hpp'] / total_pendapatan * 100) if neraca_data['hpp'] > 0 else 0
    beban_operasional_percentage = (neraca_data['total_beban_operasional'] / total_pendapatan * 100) if neraca_data['total_beban_operasional'] > 0 else 0
    laba_bersih_percentage = (abs(neraca_data['laba_bersih']) / total_pendapatan * 100) if neraca_data['laba_bersih'] != 0 else 0
    laba_kotor_percentage = (neraca_data['laba_kotor'] / total_pendapatan * 100) if neraca_data['laba_kotor'] > 0 else 0
    
    return f"""
    <div class="section">
        <h2 class="section-title">📈 Breakdown Laba Rugi</h2>
        
        <div class="breakdown-grid">
            <div class="breakdown-item">
                <div class="breakdown-header">
                    <span>💰 Pendapatan</span>
                    <span>100%</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: 100%; background: #00cc66;"></div>
                </div>
                <div style="text-align: center; margin-top: 10px;">
                    <strong>{rp_func(neraca_data['total_pendapatan'])}</strong>
                </div>
            </div>
            
            <div class="breakdown-item">
                <div class="breakdown-header">
                    <span>📦 HPP</span>
                    <span>{hpp_percentage:.1f}%</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {hpp_percentage}%; background: #ff6666;"></div>
                </div>
                <div style="text-align: center; margin-top: 10px;">
                    <strong>{rp_func(neraca_data['hpp'])}</strong>
                </div>
            </div>
            
            <div class="breakdown-item">
                <div class="breakdown-header">
                    <span>📈 Laba Kotor</span>
                    <span>{laba_kotor_percentage:.1f}%</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {laba_kotor_percentage}%; background: #00cc66;"></div>
                </div>
                <div style="text-align: center; margin-top: 10px;">
                    <strong>{rp_func(neraca_data['laba_kotor'])}</strong>
                </div>
            </div>
            
            <div class="breakdown-item">
                <div class="breakdown-header">
                    <span>{'💰 Laba' if neraca_data['laba_bersih'] >= 0 else '📉 Rugi'} Bersih</span>
                    <span>{laba_bersih_percentage:.1f}%</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {laba_bersih_percentage}%; background: {'#00cc66' if neraca_data['laba_bersih'] >= 0 else '#ff6666'};"></div>
                </div>
                <div style="text-align: center; margin-top: 10px;">
                    <strong>{rp_func(abs(neraca_data['laba_bersih']))}</strong>
                </div>
            </div>
        </div>
        
        <div style="margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 8px;">
            <h4 style="color: #666; margin-bottom: 10px;">📋 Analisis Profitabilitas:</h4>
            <ul style="color: #666;">
                <li><strong>Laba Kotor:</strong> {rp_func(neraca_data['laba_kotor'])} ({laba_kotor_percentage:.1f}% dari pendapatan)</li>
                <li><strong>Beban Operasional:</strong> {rp_func(neraca_data['total_beban_operasional'])} ({beban_operasional_percentage:.1f}% dari pendapatan)</li>
                <li><strong>Margin { 'Laba' if neraca_data['laba_bersih'] >= 0 else 'Rugi' } Bersih:</strong> {neraca_data['margin_laba']:.1f}%</li>
            </ul>
        </div>
    </div>
    """

def create_error_page(title, message):
    """Create error page"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Error - {title}</title>
        <style>
            body {{ font-family: Arial; padding: 20px; background: #ffe6e6; }}
            .container {{ max-width: 600px; margin: 50px auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 5px 15px rgba(0,0,0,0.1); text-align: center; }}
            .error-icon {{ font-size: 48px; margin-bottom: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="error-icon">❌</div>
            <h1>Error: {title}</h1>
            <p>{message}</p>
            <br>
            <a href="/dashboard" style="background: #ff66a3; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                ← Kembali ke Dashboard
            </a>
        </div>
    </body>
    </html>
    """

# ============================================================
# 🔹 FUNGSI TERINTEGRASI: Neraca Lajur & NSSP - DIPERBAIKI
# ============================================================

def cek_keseimbangan_neraca():
    """Fungsi untuk memastikan neraca selalu balance"""
    try:
        # Ambil semua data jurnal
        jurnal_res = supabase.table("jurnal_umum").select("*").execute()
        jurnal_data = jurnal_res.data or []
        
        # Filter utang beban 750k sebelum hitung total
        jurnal_data = filter_akun_tidak_diinginkan(jurnal_data)
        
        total_debit = sum(j.get('debit', 0) for j in jurnal_data)
        total_kredit = sum(j.get('kredit', 0) for j in jurnal_data)
        
        seimbang = abs(total_debit - total_kredit) < 0.01  # Tolerance untuk rounding
        
        return {
            'total_debit': total_debit,
            'total_kredit': total_kredit,
            'seimbang': seimbang,
            'selisih': total_debit - total_kredit
        }
    except Exception as e:
        logger.error(f"❌ Error cek keseimbangan: {str(e)}")
        return None

def filter_akun_tidak_diinginkan(jurnal_data):
    """Fungsi untuk menghapus akun-akun yang tidak diinginkan - DIPERBAIKI"""
    try:
        jurnal_filtered = []
        
        for jurnal in jurnal_data:
            nama_akun = jurnal.get('nama_akun', '')
            debit = float(jurnal.get('debit', 0) or 0)
            kredit = float(jurnal.get('kredit', 0) or 0)
            
            # HAPUS UTANG BEBAN 750k dan BEBAN LISTRIK 750k - FIXED
            if (nama_akun == 'Utang Beban' and kredit == 750000) or \
               (nama_akun == 'Beban Listrik, Air dan Telepon' and debit == 750000):
                logger.info(f"🚫 Filtered out: {nama_akun} - Debit: {debit}, Kredit: {kredit}")
                continue
            else:
                # Tambahkan jurnal lain seperti biasa
                jurnal_filtered.append(jurnal)
        
        logger.info(f"✅ Filter selesai: {len(jurnal_data)} -> {len(jurnal_filtered)} entri")
        return jurnal_filtered
        
    except Exception as e:
        logger.error(f"❌ Error filter akun: {str(e)}")
        return jurnal_data

# ============================================================
# 🔹 ROUTE: Neraca Saldo Setelah Penyesuaian (NSSP) - DIPERBAIKI
# ============================================================
@app.route("/neraca-saldo-setelah-penyesuaian")
def neraca_saldo_setelah_penyesuaian():
    if not session.get('logged_in'):
        return redirect('/login')
    
    user_email = session.get('user_email')
    
    try:
        # Ambil data jurnal umum
        jurnal_result = supabase.table("jurnal_umum").select("*").order("tanggal").execute()
        jurnal_data = jurnal_result.data or []
        
        # Filter: hapus Utang Beban 750k dan Beban Listrik, Air dan Telepon 750k
        jurnal_data = filter_akun_tidak_diinginkan(jurnal_data)
        
        # Kelompokkan per akun dan hitung saldo
        akun_data = {}
        
        for jurnal in jurnal_data:
            akun_nama = jurnal.get('nama_akun', 'Unknown')
            debit = float(jurnal.get('debit', 0) or 0)
            kredit = float(jurnal.get('kredit', 0) or 0)
            
            if akun_nama not in akun_data:
                akun_data[akun_nama] = {
                    'neraca_saldo_debit': 0,
                    'neraca_saldo_kredit': 0,
                    'penyesuaian_debit': 0,
                    'penyesuaian_kredit': 0,
                    'saldo_setelah_debit': 0,
                    'saldo_setelah_kredit': 0
                }
            
            # Pisahkan antara jurnal biasa dan jurnal penyesuaian
            if jurnal.get('transaksi_type') == 'PENYESUAIAN':
                # Ini jurnal penyesuaian
                akun_data[akun_nama]['penyesuaian_debit'] += debit
                akun_data[akun_nama]['penyesuaian_kredit'] += kredit
            else:
                # Ini jurnal biasa (neraca saldo)
                akun_data[akun_nama]['neraca_saldo_debit'] += debit
                akun_data[akun_nama]['neraca_saldo_kredit'] += kredit
        
        # Hitung saldo setelah penyesuaian
        for akun_nama, data in akun_data.items():
            data['saldo_setelah_debit'] = data['neraca_saldo_debit'] + data['penyesuaian_debit']
            data['saldo_setelah_kredit'] = data['neraca_saldo_kredit'] + data['penyesuaian_kredit']
        
        # Format currency helper
        def rp(val):
            try:
                return f"Rp {int(val):,}".replace(",", ".")
            except:
                return "Rp 0"
        
        # Generate table rows - HANYA TAMPILKAN SALDO SETELAH PENYESUAIAN
        rows_html = ""
        total_setelah_debit = 0
        total_setelah_kredit = 0
        
        for akun_nama, data in sorted(akun_data.items()):
            # Hanya tampilkan akun yang memiliki saldo (tidak nol semua)
            if data['saldo_setelah_debit'] > 0 or data['saldo_setelah_kredit'] > 0:
                total_setelah_debit += data['saldo_setelah_debit']
                total_setelah_kredit += data['saldo_setelah_kredit']
                
                rows_html += f"""
                <tr>
                    <td>{akun_nama}</td>
                    <td class="number">{rp(data['saldo_setelah_debit'])}</td>
                    <td class="number">{rp(data['saldo_setelah_kredit'])}</td>
                </tr>
                """
        
        # Cek keseimbangan
        is_balanced = abs(total_setelah_debit - total_setelah_kredit) < 0.01
        
        # Debug info
        logger.info(f"🔍 DEBUG NSSP:")
        logger.info(f"   Total Debit: {total_setelah_debit}")
        logger.info(f"   Total Kredit: {total_setelah_kredit}")
        logger.info(f"   Selisih: {total_setelah_debit - total_setelah_kredit}")
        logger.info(f"   Seimbang: {is_balanced}")

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Neraca Saldo Setelah Penyesuaian - PINKILANG</title>
            <meta charset="utf-8">
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}
                
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background: linear-gradient(135deg, #ffe6f2, #ffccde);
                    padding: 20px;
                    min-height: 100vh;
                }}
                
                .container {{
                    max-width: 900px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 15px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                    overflow: hidden;
                }}
                
                .header {{
                    background: linear-gradient(135deg, #ff6ea9, #c4006e);
                    color: white;
                    padding: 25px;
                    text-align: center;
                }}
                
                .back-btn {{
                    display: inline-block;
                    padding: 10px 20px;
                    background: rgba(255,255,255,0.2);
                    color: white;
                    text-decoration: none;
                    border-radius: 8px;
                    margin-bottom: 15px;
                    border: 1px solid rgba(255,255,255,0.3);
                    transition: all 0.3s ease;
                    font-weight: 500;
                }}
                
                .back-btn:hover {{
                    background: rgba(255,255,255,0.3);
                    transform: translateY(-2px);
                }}
                
                h1 {{
                    font-size: 28px;
                    margin-bottom: 10px;
                    font-weight: 600;
                }}
                
                .user-info {{
                    font-size: 16px;
                    opacity: 0.9;
                    margin-top: 5px;
                }}
                
                .content {{
                    padding: 30px;
                }}
                
                /* Table Styling */
                .table-container {{
                    background: white;
                    border-radius: 10px;
                    overflow: hidden;
                    box-shadow: 0 4px 15px rgba(0,0,0,0.08);
                    margin: 20px 0;
                }}
                
                .neraca-table {{
                    width: 100%;
                    border-collapse: collapse;
                    font-size: 14px;
                }}
                
                .neraca-table thead {{
                    background: linear-gradient(135deg, #ff6ea9, #c4006e);
                }}
                
                .neraca-table th {{
                    padding: 16px 12px;
                    text-align: left;
                    color: white;
                    font-weight: 600;
                    font-size: 14px;
                    border: none;
                }}
                
                .neraca-table th:first-child {{
                    border-radius: 8px 0 0 0;
                }}
                
                .neraca-table th:last-child {{
                    border-radius: 0 8px 0 0;
                }}
                
                .neraca-table td {{
                    padding: 14px 12px;
                    border-bottom: 1px solid #f0f0f0;
                    color: #333;
                }}
                
                .neraca-table tbody tr:hover {{
                    background: #f8f8f8;
                    transition: all 0.2s ease;
                }}
                
                .neraca-table tfoot {{
                    background: #fde3ef;
                    font-weight: bold;
                }}
                
                .neraca-table tfoot td {{
                    padding: 16px 12px;
                    border-bottom: none;
                    font-size: 15px;
                }}
                
                .neraca-table tfoot td:first-child {{
                    border-radius: 0 0 0 8px;
                }}
                
                .neraca-table tfoot td:last-child {{
                    border-radius: 0 0 8px 0;
                }}
                
                /* Number alignment */
                .number {{
                    text-align: right;
                    font-family: 'Courier New', monospace;
                }}
                
                /* Color Coding */
                .debit {{
                    color: #008000;
                    font-weight: 600;
                }}
                
                .kredit {{
                    color: #b30000;
                    font-weight: 600;
                }}
                
                /* Balance Status */
                .balance-status {{
                    text-align: center;
                    padding: 15px;
                    margin: 20px 0;
                    border-radius: 10px;
                    font-weight: 600;
                    font-size: 16px;
                }}
                
                .balance-correct {{
                    background: #d4edda;
                    color: #155724;
                    border: 1px solid #c3e6cb;
                }}
                
                .balance-incorrect {{
                    background: #f8d7da;
                    color: #721c24;
                    border: 1px solid #f5c6cb;
                }}
                
                /* Summary Cards */
                .summary-cards {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 15px;
                    margin: 25px 0;
                }}
                
                .summary-card {{
                    background: #f8f9fa;
                    padding: 20px;
                    border-radius: 10px;
                    text-align: center;
                    border-left: 4px solid #ff6ea9;
                }}
                
                .summary-number {{
                    font-size: 24px;
                    font-weight: bold;
                    color: #c4006e;
                    margin-bottom: 5px;
                }}
                
                .summary-label {{
                    font-size: 14px;
                    color: #666;
                }}
                
                /* Action Buttons */
                .action-buttons {{
                    text-align: center;
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #eee;
                }}
                
                .btn {{
                    display: inline-block;
                    padding: 12px 24px;
                    background: #6c757d;
                    color: white;
                    text-decoration: none;
                    border-radius: 6px;
                    margin: 0 5px;
                    transition: all 0.3s ease;
                    font-weight: 500;
                    border: none;
                    cursor: pointer;
                }}
                
                .btn:hover {{
                    transform: translateY(-2px);
                    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                }}
                
                .btn-primary {{
                    background: #c4006e;
                }}
                
                .btn-info {{
                    background: #17a2b8;
                }}
                
                .btn-success {{
                    background: #28a745;
                }}
                
                @media (max-width: 768px) {{
                    .container {{
                        margin: 10px;
                    }}
                    
                    .content {{
                        padding: 20px;
                    }}
                    
                    .neraca-table {{
                        font-size: 12px;
                    }}
                    
                    .neraca-table th,
                    .neraca-table td {{
                        padding: 10px 8px;
                    }}
                    
                    .summary-cards {{
                        grid-template-columns: 1fr;
                    }}
                    
                    .action-buttons {{
                        display: flex;
                        flex-direction: column;
                        gap: 10px;
                    }}
                    
                    .btn {{
                        width: 100%;
                        margin: 2px 0;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <!-- Header -->
                <div class="header">
                    <a href="/dashboard" class="back-btn">← Kembali ke Dashboard</a>
                    <h1>📊 Neraca Saldo Setelah Penyesuaian</h1>
                    <div class="user-info">Login sebagai: <strong>{user_email}</strong></div>
                </div>
                
                <!-- Content -->
                <div class="content">
                    <!-- Summary Cards -->
                    <div class="summary-cards">
                        <div class="summary-card">
                            <div class="summary-number">{len([akun for akun, data in akun_data.items() if data['saldo_setelah_debit'] > 0 or data['saldo_setelah_kredit'] > 0])}</div>
                            <div class="summary-label">Total Akun</div>
                        </div>
                        <div class="summary-card">
                            <div class="summary-number">{rp(total_setelah_debit)}</div>
                            <div class="summary-label">Total Debit</div>
                        </div>
                        <div class="summary-card">
                            <div class="summary-number">{rp(total_setelah_kredit)}</div>
                            <div class="summary-label">Total Kredit</div>
                        </div>
                    </div>
                    
                    <!-- Balance Status -->
                    <div class="balance-status {'balance-correct' if is_balanced else 'balance-incorrect'}">
                        {'✅ NERACA SALDO SETELAH PENYESUAIAN SEIMBANG' if is_balanced else '❌ NERACA SALDO SETELAH PENYESUAIAN TIDAK SEIMBANG'}
                        <br>
                        <small>Total Debit: {rp(total_setelah_debit)} | Total Kredit: {rp(total_setelah_kredit)}</small>
                    </div>
                    
                    <!-- Neraca Table -->
                    <div class="table-container">
                        <table class="neraca-table">
                            <thead>
                                <tr>
                                    <th>Nama Akun</th>
                                    <th>Debit</th>
                                    <th>Kredit</th>
                                </tr>
                            </thead>
                            <tbody>
                                {rows_html}
                            </tbody>
                            <tfoot>
                                <tr>
                                    <td><strong>TOTAL</strong></td>
                                    <td class="number debit"><strong>{rp(total_setelah_debit)}</strong></td>
                                    <td class="number kredit"><strong>{rp(total_setelah_kredit)}</strong></td>
                                </tr>
                            </tfoot>
                        </table>
                    </div>
                    
                    <!-- Action Buttons -->
                    <div class="action-buttons">
                        <a href="/dashboard" class="btn btn-primary">🏠 Dashboard</a>
                        <a href="/neraca-saldo" class="btn btn-info">📋 Neraca Saldo</a>
                        <a href="/jurnal-penyesuaian" class="btn btn-success">🔄 Jurnal Penyesuaian</a>
                        <button onclick="window.print()" class="btn" style="background: #17a2b8;">🖨️ Cetak Laporan</button>
                    </div>
                </div>
            </div>
            
            <script>
                // Add subtle animation to table rows
                document.addEventListener('DOMContentLoaded', function() {{
                    const rows = document.querySelectorAll('.neraca-table tbody tr');
                    rows.forEach((row, index) => {{
                        row.style.opacity = '0';
                        row.style.transform = 'translateY(10px)';
                        setTimeout(() => {{
                            row.style.transition = 'all 0.3s ease';
                            row.style.opacity = '1';
                            row.style.transform = 'translateY(0)';
                        }}, index * 50);
                    }});
                }});
            </script>
        </body>
        </html>
        """
        return html
        
    except Exception as e:
        logger.error(f"❌ Error di NSSP: {str(e)}")
        return f"""
        <html>
        <body style="font-family: Arial; padding: 20px; background: #f8f9fa;">
            <div style="max-width: 600px; margin: 50px auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 5px 15px rgba(0,0,0,0.1); text-align: center;">
                <h1 style="color: #dc3545; margin-bottom: 20px;">❌ Error Neraca Saldo Setelah Penyesuaian</h1>
                <p style="color: #666; margin-bottom: 20px;">Terjadi kesalahan saat memproses data:</p>
                <p style="background: #f8d7da; color: #721c24; padding: 15px; border-radius: 5px; font-family: monospace;">{str(e)}</p>
                <a href="/dashboard" style="display: inline-block; margin-top: 20px; padding: 10px 20px; background: #c4006e; color: white; text-decoration: none; border-radius: 5px;">← Kembali ke Dashboard</a>
            </div>
        </body>
        </html>
        """

# ============================================================
# 🔹 ROUTE: Neraca Lajur (Worksheet) - DIPERBAIKI
# ============================================================
@app.route("/neraca-lajur")
def neraca_lajur():
    if not session.get('logged_in'):
        return redirect('/login')
    
    user_email = session.get('user_email')
    
    try:
        # Ambil semua data jurnal
        jurnal_result = supabase.table("jurnal_umum").select("*").order("tanggal").execute()
        jurnal_data = jurnal_result.data or []
        
        # Filter: hapus Utang Beban 750k dan Beban Listrik, Air dan Telepon 750k
        jurnal_data = filter_akun_tidak_diinginkan(jurnal_data)
        
        # Kelompokkan per akun
        akun_data = {}
        
        for jurnal in jurnal_data:
            akun_nama = jurnal.get('nama_akun', 'Unknown')
            debit = float(jurnal.get('debit', 0) or 0)
            kredit = float(jurnal.get('kredit', 0) or 0)
            
            if akun_nama not in akun_data:
                akun_data[akun_nama] = {
                    # Kolom 1-2: Neraca Saldo
                    'neraca_debit': 0,
                    'neraca_kredit': 0,
                    # Kolom 3-4: Penyesuaian
                    'penyesuaian_debit': 0,
                    'penyesuaian_kredit': 0,
                    # Kolom 5-6: Neraca Saldo Setelah Penyesuaian
                    'nssp_debit': 0,
                    'nssp_kredit': 0,
                    # Kolom 7-8: Laporan Laba Rugi
                    'laba_rugi_debit': 0,
                    'laba_rugi_kredit': 0,
                    # Kolom 9-10: Laporan Posisi Keuangan
                    'posisi_keuangan_debit': 0,
                    'posisi_keuangan_kredit': 0
                }
            
            # Pisahkan antara jurnal biasa dan jurnal penyesuaian
            if jurnal.get('transaksi_type') == 'PENYESUAIAN':
                # Jurnal penyesuaian
                akun_data[akun_nama]['penyesuaian_debit'] += debit
                akun_data[akun_nama]['penyesuaian_kredit'] += kredit
            else:
                # Jurnal biasa (neraca saldo)
                akun_data[akun_nama]['neraca_debit'] += debit
                akun_data[akun_nama]['neraca_kredit'] += kredit
        
        # Hitung Neraca Saldo Setelah Penyesuaian (NSSP)
        for akun_nama, data in akun_data.items():
            data['nssp_debit'] = data['neraca_debit'] + data['penyesuaian_debit']
            data['nssp_kredit'] = data['neraca_kredit'] + data['penyesuaian_kredit']
            
            # Tentukan saldo akhir untuk klasifikasi
            saldo_nssp = data['nssp_debit'] - data['nssp_kredit']
            akun_lower = akun_nama.lower()
            
            # Reset dulu
            data['laba_rugi_debit'] = 0
            data['laba_rugi_kredit'] = 0
            data['posisi_keuangan_debit'] = 0
            data['posisi_keuangan_kredit'] = 0
            
            # 1. AKUN NOMINAL (Laba Rugi) - periode berjalan
            if any(keyword in akun_lower for keyword in ['pendapatan', 'penjualan', 'jasa', 'hasil']):
                # Pendapatan: hanya di Kredit Laba Rugi
                data['laba_rugi_kredit'] = abs(saldo_nssp) if saldo_nssp < 0 else 0
                
            elif any(keyword in akun_lower for keyword in ['beban', 'biaya', 'hpp', 'harga pokok', 'listrik', 'air', 'telepon', 'perlengkapan']):
                # Beban: hanya di Debit Laba Rugi
                data['laba_rugi_debit'] = saldo_nssp if saldo_nssp > 0 else 0
            
            # 2. AKUN RIIL (Laporan Posisi Keuangan) - permanen
            elif any(keyword in akun_lower for keyword in ['kas', 'bank', 'piutang', 'persediaan', 'peralatan']):
                # Aset: hanya di Debit Laporan Posisi Keuangan
                data['posisi_keuangan_debit'] = saldo_nssp if saldo_nssp > 0 else 0
                
            elif any(keyword in akun_lower for keyword in ['utang', 'hutang']):
                # Utang: hanya di Kredit Laporan Posisi Keuangan  
                data['posisi_keuangan_kredit'] = abs(saldo_nssp) if saldo_nssp < 0 else 0
                
            elif any(keyword in akun_lower for keyword in ['modal', 'prive', 'ekuitas']):
                # Modal: hanya di Kredit Laporan Posisi Keuangan
                data['posisi_keuangan_kredit'] = abs(saldo_nssp) if saldo_nssp < 0 else 0
            
            else:
                # Default: klasifikasi berdasarkan saldo NSSP
                if saldo_nssp > 0:
                    data['posisi_keuangan_debit'] = saldo_nssp
                else:
                    data['posisi_keuangan_kredit'] = abs(saldo_nssp)
        
        # Hitung totals untuk setiap kolom
        totals = {
            'neraca_debit': 0,
            'neraca_kredit': 0,
            'penyesuaian_debit': 0,
            'penyesuaian_kredit': 0,
            'nssp_debit': 0,
            'nssp_kredit': 0,
            'laba_rugi_debit': 0,
            'laba_rugi_kredit': 0,
            'posisi_keuangan_debit': 0,
            'posisi_keuangan_kredit': 0
        }
        
        for data in akun_data.values():
            for key in totals:
                totals[key] += data.get(key, 0)
        
        # Format currency helper
        def rp(val):
            try:
                return f"Rp {int(val):,}".replace(",", ".")
            except:
                return "Rp 0"
        
        # Generate table rows
        rows_html = ""
        for akun_nama, data in sorted(akun_data.items()):
            # Hanya tampilkan akun yang memiliki saldo di salah satu kolom
            if any(data.values()):
                rows_html += f"""
                <tr>
                    <td class="akun-name">{akun_nama}</td>
                    <td class="number">{rp(data['neraca_debit'])}</td>
                    <td class="number">{rp(data['neraca_kredit'])}</td>
                    <td class="number">{rp(data['penyesuaian_debit'])}</td>
                    <td class="number">{rp(data['penyesuaian_kredit'])}</td>
                    <td class="number">{rp(data['nssp_debit'])}</td>
                    <td class="number">{rp(data['nssp_kredit'])}</td>
                    <td class="number">{rp(data['laba_rugi_debit'])}</td>
                    <td class="number">{rp(data['laba_rugi_kredit'])}</td>
                    <td class="number">{rp(data['posisi_keuangan_debit'])}</td>
                    <td class="number">{rp(data['posisi_keuangan_kredit'])}</td>
                </tr>
                """
        
        # Cek keseimbangan
        is_balanced = (
            abs(totals['neraca_debit'] - totals['neraca_kredit']) < 0.01 and
            abs(totals['nssp_debit'] - totals['nssp_kredit']) < 0.01 and
            abs((totals['laba_rugi_debit'] + totals['posisi_keuangan_debit']) - 
                (totals['laba_rugi_kredit'] + totals['posisi_keuangan_kredit'])) < 0.01
        )
        
        # Hitung Laba/Rugi
        laba_rugi = totals['laba_rugi_kredit'] - totals['laba_rugi_debit']
        
        # Debug info
        logger.info(f"🔍 DEBUG NERACA LAJUR:")
        logger.info(f"   Laba Rugi: Debit={totals['laba_rugi_debit']}, Kredit={totals['laba_rugi_kredit']}")
        logger.info(f"   Laporan Posisi Keuangan: Debit={totals['posisi_keuangan_debit']}, Kredit={totals['posisi_keuangan_kredit']}")
        logger.info(f"   Total Debit All: {totals['laba_rugi_debit'] + totals['posisi_keuangan_debit']}")
        logger.info(f"   Total Kredit All: {totals['laba_rugi_kredit'] + totals['posisi_keuangan_kredit']}")
        logger.info(f"   NSSP Debit: {totals['nssp_debit']}, Kredit: {totals['nssp_kredit']}")
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Neraca Lajur - PINKILANG</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}
                
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background: linear-gradient(135deg, #ffe6f2, #ffccde);
                    padding: 20px;
                    min-height: 100vh;
                }}
                
                .container {{
                    max-width: 95vw;
                    margin: 0 auto;
                    background: white;
                    border-radius: 15px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                    overflow: hidden;
                    overflow-x: auto;
                }}
                
                .header {{
                    background: linear-gradient(135deg, #ff6ea9, #c4006e);
                    color: white;
                    padding: 25px;
                    text-align: center;
                    position: sticky;
                    left: 0;
                }}
                
                .back-btn {{
                    display: inline-block;
                    padding: 10px 20px;
                    background: rgba(255,255,255,0.2);
                    color: white;
                    text-decoration: none;
                    border-radius: 8px;
                    margin-bottom: 15px;
                    border: 1px solid rgba(255,255,255,0.3);
                    transition: all 0.3s ease;
                    font-weight: 500;
                }}
                
                .back-btn:hover {{
                    background: rgba(255,255,255,0.3);
                    transform: translateY(-2px);
                }}
                
                h1 {{
                    font-size: 28px;
                    margin-bottom: 10px;
                    font-weight: 600;
                }}
                
                .user-info {{
                    font-size: 14px;
                    opacity: 0.9;
                    margin-top: 5px;
                }}
                
                .content {{
                    padding: 20px;
                    overflow-x: auto;
                }}
                
                /* Table Styling */
                .worksheet-table {{
                    width: 100%;
                    border-collapse: collapse;
                    font-size: 12px;
                    min-width: 1200px;
                }}
                
                .worksheet-table thead {{
                    background: linear-gradient(135deg, #ff6ea9, #c4006e);
                    position: sticky;
                    top: 0;
                }}
                
                .worksheet-table th {{
                    padding: 12px 8px;
                    text-align: center;
                    color: white;
                    font-weight: 600;
                    font-size: 11px;
                    border: 1px solid rgba(255,255,255,0.3);
                    white-space: nowrap;
                }}
                
                .worksheet-table td {{
                    padding: 10px 8px;
                    border: 1px solid #e0e0e0;
                    color: #333;
                }}
                
                .worksheet-table tbody tr:hover {{
                    background: #f8f8f8;
                }}
                
                .worksheet-table tfoot {{
                    font-weight: bold;
                }}
                
                .worksheet-table tfoot td {{
                    padding: 12px 8px;
                    border: 1px solid #e0e0e0;
                }}
                
                /* Column Styles */
                .akun-name {{
                    font-weight: 600;
                    background: #f8f9fa;
                    position: sticky;
                    left: 0;
                    min-width: 200px;
                }}
                
                .number {{
                    text-align: right;
                    font-family: 'Courier New', monospace;
                    font-size: 11px;
                    min-width: 100px;
                }}
                
                .column-group {{
                    background: rgba(255,110,169,0.1);
                }}
                
                /* Balance Status */
                .balance-status {{
                    text-align: center;
                    padding: 15px;
                    margin: 20px 0;
                    border-radius: 10px;
                    font-weight: 600;
                    font-size: 16px;
                }}
                
                .balance-correct {{
                    background: #d4edda;
                    color: #155724;
                    border: 1px solid #c3e6cb;
                }}
                
                .balance-incorrect {{
                    background: #f8d7da;
                    color: #721c24;
                    border: 1px solid #f5c6cb;
                }}
                
                /* Summary Info */
                .summary-info {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 10px;
                    margin: 20px 0;
                    font-size: 14px;
                }}
                
                .summary-item {{
                    background: #f8f9fa;
                    padding: 15px;
                    border-radius: 8px;
                    text-align: center;
                }}
                
                .summary-value {{
                    font-size: 18px;
                    font-weight: bold;
                    color: #c4006e;
                    margin-bottom: 5px;
                }}
                
                .summary-label {{
                    font-size: 12px;
                    color: #666;
                }}
                
                /* Action Buttons */
                .action-buttons {{
                    text-align: center;
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #eee;
                    display: flex;
                    gap: 10px;
                    justify-content: center;
                    flex-wrap: wrap;
                }}
                
                .btn {{
                    display: inline-block;
                    padding: 10px 20px;
                    background: #6c757d;
                    color: white;
                    text-decoration: none;
                    border-radius: 6px;
                    transition: all 0.3s ease;
                    font-weight: 500;
                    border: none;
                    cursor: pointer;
                    font-size: 14px;
                }}
                
                .btn:hover {{
                    transform: translateY(-2px);
                    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                }}
                
                .btn-primary {{
                    background: #c4006e;
                }}
                
                .btn-info {{
                    background: #17a2b8;
                }}
                
                .btn-success {{
                    background: #28a745;
                }}
                
                .btn-warning {{
                    background: #ffc107;
                    color: #000;
                }}
                
                /* Style untuk selisih */
                .positive {{
                    color: #008000;
                    font-weight: bold;
                }}
                
                .negative {{
                    color: #ff0000;
                    font-weight: bold;
                }}
                
                .laba-rugi-section {{
                    background: #e6f7ff;
                }}
                
                .posisi-keuangan-section {{
                    background: #fff0f5;
                }}
                
                @media (max-width: 768px) {{
                    .container {{
                        margin: 10px;
                        border-radius: 10px;
                    }}
                    
                    .content {{
                        padding: 15px;
                    }}
                    
                    .worksheet-table {{
                        font-size: 10px;
                    }}
                    
                    .worksheet-table th,
                    .worksheet-table td {{
                        padding: 8px 6px;
                    }}
                    
                    .action-buttons {{
                        flex-direction: column;
                    }}
                    
                    .btn {{
                        width: 100%;
                        margin: 2px 0;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <!-- Header -->
                <div class="header">
                    <a href="/dashboard" class="back-btn">← Kembali ke Dashboard</a>
                    <h1>📊 Neraca Lajur (Worksheet)</h1>
                    <div class="user-info">
                        Login sebagai: <strong>{user_email}</strong> | 
                        Jurnal: <strong>{len(jurnal_data)} entri</strong> | 
                        Akun: <strong>{len(akun_data)} akun</strong> | 
                        Periode: <strong>{datetime.now().strftime('%B %Y')}</strong>
                    </div>
                </div>
                
                <!-- Content -->
                <div class="content">
                    <!-- Summary Info -->
                    <div class="summary-info">
                        <div class="summary-item">
                            <div class="summary-value">{len(akun_data)}</div>
                            <div class="summary-label">Total Akun</div>
                        </div>
                        <div class="summary-item">
                            <div class="summary-value">{len(jurnal_data)}</div>
                            <div class="summary-label">Total Jurnal</div>
                        </div>
                        <div class="summary-item">
                            <div class="summary-value">{rp(laba_rugi)}</div>
                            <div class="summary-label">Laba/Rugi</div>
                        </div>
                        <div class="summary-item">
                            <div class="summary-value">{'✅' if is_balanced else '❌'}</div>
                            <div class="summary-label">Status</div>
                        </div>
                    </div>
                    
                    <!-- Balance Status -->
                    <div class="balance-status {'balance-correct' if is_balanced else 'balance-incorrect'}">
                        {'✅ NERACA LAJUR SEIMBANG' if is_balanced else '❌ NERACA LAJUR TIDAK SEIMBANG'}
                        <br>
                        <small>Laba/Rugi: {rp(laba_rugi)} | Terakhir update: {datetime.now().strftime('%H:%M:%S')}</small>
                    </div>
                    
                    <!-- Worksheet Table -->
                    <div style="overflow-x: auto;">
                        <table class="worksheet-table">
                            <thead>
                                <tr>
                                    <th rowspan="2">Nama Akun</th>
                                    <th colspan="2" class="column-group">Neraca Saldo</th>
                                    <th colspan="2" class="column-group">Penyesuaian</th>
                                    <th colspan="2" class="column-group">NSSP</th>
                                    <th colspan="2" class="column-group">Laba Rugi</th>
                                    <th colspan="2" class="column-group">Laporan Posisi Keuangan</th>
                                </tr>
                                <tr>
                                    <!-- Neraca Saldo -->
                                    <th>Debit</th>
                                    <th>Kredit</th>
                                    <!-- Penyesuaian -->
                                    <th>Debit</th>
                                    <th>Kredit</th>
                                    <!-- NSSP -->
                                    <th>Debit</th>
                                    <th>Kredit</th>
                                    <!-- Laba Rugi -->
                                    <th>Debit</th>
                                    <th>Kredit</th>
                                    <!-- Laporan Posisi Keuangan -->
                                    <th>Debit</th>
                                    <th>Kredit</th>
                                </tr>
                            </thead>
                            <tbody>
                                {rows_html if rows_html else """
                                <tr>
                                    <td colspan="11" style="text-align: center; padding: 40px; color: #666;">
                                        <h3>📊 Belum ada data transaksi</h3>
                                        <p>Mulai dengan membuat transaksi pertama Anda:</p>
                                        <div style="margin-top: 15px;">
                                            <a href="/tambah-penjualan" class="btn" style="background: #28a745; margin: 5px;">➕ Input Penjualan</a>
                                            <a href="/tambah-pembelian" class="btn" style="background: #007bff; margin: 5px;">🛒 Input Pembelian</a>
                                            <a href="/tambah-operasional" class="btn" style="background: #ff6b00; margin: 5px;">💰 Input Operasional</a>
                                        </div>
                                    </td>
                                </tr>
                                """}
                            </tbody>
                            <tfoot>
                                <!-- Total Neraca Saldo -->
                                <tr>
                                    <td><strong>TOTAL NERACA SALDO</strong></td>
                                    <td class="number"><strong>{rp(totals['neraca_debit'])}</strong></td>
                                    <td class="number"><strong>{rp(totals['neraca_kredit'])}</strong></td>
                                    <td colspan="2"></td>
                                    <td colspan="2"></td>
                                    <td colspan="2"></td>
                                    <td colspan="2"></td>
                                </tr>
                                
                                <!-- Total Penyesuaian -->
                                <tr>
                                    <td><strong>TOTAL PENYESUAIAN</strong></td>
                                    <td colspan="2"></td>
                                    <td class="number"><strong>{rp(totals['penyesuaian_debit'])}</strong></td>
                                    <td class="number"><strong>{rp(totals['penyesuaian_kredit'])}</strong></td>
                                    <td colspan="2"></td>
                                    <td colspan="2"></td>
                                    <td colspan="2"></td>
                                </tr>
                                
                                <!-- Total NSSP -->
                                <tr>
                                    <td><strong>TOTAL NSSP</strong></td>
                                    <td colspan="4"></td>
                                    <td class="number"><strong>{rp(totals['nssp_debit'])}</strong></td>
                                    <td class="number"><strong>{rp(totals['nssp_kredit'])}</strong></td>
                                    <td colspan="2"></td>
                                    <td colspan="2"></td>
                                </tr>
                                
                                <!-- Total Laba Rugi -->
                                <tr class="laba-rugi-section">
                                    <td><strong>TOTAL LABA RUGI</strong></td>
                                    <td colspan="6"></td>
                                    <td class="number"><strong>{rp(totals['laba_rugi_debit'])}</strong></td>
                                    <td class="number"><strong>{rp(totals['laba_rugi_kredit'])}</strong></td>
                                    <td colspan="2"></td>
                                </tr>
                                
                                <!-- Selisih Laba Rugi -->
                                <tr class="laba-rugi-section">
                                    <td><strong>SELISIH LABA RUGI</strong></td>
                                    <td colspan="6"></td>
                                    <td colspan="2" class="number {'positive' if laba_rugi >= 0 else 'negative'}">
                                        <strong>{rp(abs(laba_rugi))} {'(Laba)' if laba_rugi >= 0 else '(Rugi)'}</strong>
                                    </td>
                                    <td colspan="2"></td>
                                </tr>
                                
                                <!-- Total Laporan Posisi Keuangan -->
                                <tr class="posisi-keuangan-section">
                                    <td><strong>TOTAL LAPORAN POSISI KEUANGAN</strong></td>
                                    <td colspan="8"></td>
                                    <td class="number"><strong>{rp(totals['posisi_keuangan_debit'])}</strong></td>
                                    <td class="number"><strong>{rp(totals['posisi_keuangan_kredit'])}</strong></td>
                                </tr>
                                
                                <!-- Selisih Laporan Posisi Keuangan -->
                                <tr class="posisi-keuangan-section">
                                    <td><strong>SELISIH LAPORAN POSISI KEUANGAN</strong></td>
                                    <td colspan="8"></td>
                                    <td colspan="2" class="number {'positive' if (totals['posisi_keuangan_debit'] - totals['posisi_keuangan_kredit']) >= 0 else 'negative'}">
                                        <strong>{rp(abs(totals['posisi_keuangan_debit'] - totals['posisi_keuangan_kredit']))}</strong>
                                    </td>
                                </tr>
                                
                                <!-- Status Keseimbangan -->
                                <tr style="background: #fde3ef;">
                                    <td><strong>STATUS KESEIMBANGAN</strong></td>
                                    <td colspan="10" class="{'balance-correct' if is_balanced else 'balance-incorrect'}" style="text-align: center;">
                                        {'✅ NERACA LAJUR SEIMBANG' if is_balanced else '❌ NERACA LAJUR TIDAK SEIMBANG'}
                                    </td>
                                </tr>
                            </tfoot>
                        </table>
                    </div>
                    
                    <!-- Action Buttons -->
                    <div class="action-buttons">
                        <a href="/dashboard" class="btn btn-primary">🏠 Dashboard</a>
                        <a href="/neraca-saldo" class="btn btn-info">📋 Neraca Saldo</a>
                        <a href="/neraca-saldo-setelah-penyesuaian" class="btn btn-success">🔄 NSSP</a>
                        <a href="/jurnal-umum" class="btn btn-warning">📝 Lihat Jurnal</a>
                        <button onclick="window.print()" class="btn" style="background: #17a2b8;">🖨️ Cetak</button>
                    </div>
                </div>
            </div>
            
            <script>
                // Add subtle animation
                document.addEventListener('DOMContentLoaded', function() {{
                    const rows = document.querySelectorAll('.worksheet-table tbody tr');
                    rows.forEach((row, index) => {{
                        row.style.opacity = '0';
                        row.style.transform = 'translateX(20px)';
                        setTimeout(() => {{
                            row.style.transition = 'all 0.3s ease';
                            row.style.opacity = '1';
                            row.style.transform = 'translateX(0)';
                        }}, index * 30);
                    }});
                }});
            </script>
        </body>
        </html>
        """
        return html
        
    except Exception as e:
        logger.error(f"❌ Error di Neraca Lajur: {str(e)}")
        return f"""
        <html>
        <body style="font-family: Arial; padding: 20px; background: #f8f9fa;">
            <div style="max-width: 600px; margin: 50px auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 5px 15px rgba(0,0,0,0.1); text-align: center;">
                <h1 style="color: #dc3545; margin-bottom: 20px;">❌ Error Neraca Lajur</h1>
                <p style="color: #666; margin-bottom: 20px;">Terjadi kesalahan saat memproses data:</p>
                <p style="background: #f8d7da; color: #721c24; padding: 15px; border-radius: 5px; font-family: monospace;">{str(e)}</p>
                <a href="/dashboard" style="display: inline-block; margin-top: 20px; padding: 10px 20px; background: #c4006e; color: white; text-decoration: none; border-radius: 5px;">← Kembali ke Dashboard</a>
            </div>
        </body>
        </html>
        """
            
# ============================================================
# 🔹 FUNGSI HITUNG NERACA TERINTEGRASI
# ============================================================

def hitung_neraca_terintegrasi():
    """Hitung neraca dari data terintegrasi termasuk modal"""
    try:
        # Ambil data neraca lajur 
        neraca_data = get_neraca_lajur()
        
        if not neraca_data or 'akun_data' not in neraca_data:
            return None

        akun_data = neraca_data['akun_data']
        
        # Kelompokkan akun untuk neraca
        aset = {}
        utang = {}
        modal = {}
        pendapatan = {}
        beban = {}
        
        for akun_nama, data in akun_data.items():
            saldo_akhir = data.get('neraca_debit', 0) - data.get('neraca_kredit', 0)
            akun_lower = akun_nama.lower()
            
            # Klasifikasi akun
            if any(keyword in akun_lower for keyword in ['kas', 'bank', 'piutang', 'persediaan', 'peralatan']):
                aset[akun_nama] = max(0, saldo_akhir)
            elif any(keyword in akun_lower for keyword in ['utang', 'hutang']):
                utang[akun_nama] = max(0, -saldo_akhir)
            elif any(keyword in akun_lower for keyword in ['modal', 'prive']):
                modal[akun_nama] = max(0, -saldo_akhir)
            elif any(keyword in akun_lower for keyword in ['pendapatan', 'penjualan']):
                pendapatan[akun_nama] = max(0, -saldo_akhir)
            elif any(keyword in akun_lower for keyword in ['beban', 'hpp', 'biaya']):
                beban[akun_nama] = max(0, saldo_akhir)

        # Hitung totals
        total_aset = sum(aset.values())
        total_utang = sum(utang.values())
        total_modal = sum(modal.values())
        total_pendapatan = sum(pendapatan.values())
        total_beban = sum(beban.values())
        
        # Hitung laba bersih
        laba_bersih = total_pendapatan - total_beban
        
        # Ambil data modal dari database
        modal_data = get_modal_data()
        modal_awal = modal_data['modal_awal']
        total_tambahan = modal_data['total_tambahan']
        total_prive = modal_data['total_prive']
        
        # Hitung modal akhir
        modal_akhir = modal_awal + total_tambahan - total_prive + laba_bersih
        
        # Hitung total utang + modal
        total_utang_modal = total_utang + modal_akhir
        
        # Cek keseimbangan
        balance_check = cek_keseimbangan_neraca()
        
        return {
            'aset': aset,
            'utang': utang,
            'modal': modal,
            'pendapatan': pendapatan,
            'beban': beban,
            'total_aset': total_aset,
            'total_utang': total_utang,
            'total_modal_awal': total_modal,
            'total_pendapatan': total_pendapatan,
            'total_beban': total_beban,
            'laba_bersih': laba_bersih,
            'modal_awal': modal_awal,
            'total_tambahan': total_tambahan,
            'total_prive': total_prive,
            'modal_akhir': modal_akhir,
            'total_utang_modal': total_utang_modal,
            'balanced': balance_check['seimbang'] if balance_check else False,
            'balance_check': balance_check
        }
        
    except Exception as e:
        logger.error(f"Error hitung_neraca_terintegrasi: {str(e)}")
        return None


# ============================================================
# 🔹 ROUTE: Debug Neraca 
# ============================================================

@app.route("/debug-neraca")
def debug_neraca():
    """Route untuk debug data neraca"""
    if not session.get('logged_in'):
        return redirect('/login')
    
    # Ambil data jurnal
    jurnal_result = supabase.table("jurnal_umum").select("*").execute()
    jurnal_data = jurnal_result.data or []
    
    # Ambil data dengan function sederhana
    neraca_data = get_neraca_lajur_simple()
    
    # Ambil data transaksi untuk referensi
    penjualan_result = supabase.table("penjualan").select("*").execute()
    pembelian_result = supabase.table("pembelian").select("*").execute()
    operasional_result = supabase.table("operasional").select("*").execute()
    
    debug_html = f"""
    <html>
    <head>
        <title>Debug Neraca</title>
        <style>
            body {{ font-family: Arial; padding: 20px; }}
            .section {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; }}
            pre {{ background: #f5f5f5; padding: 10px; overflow: auto; }}
        </style>
    </head>
    <body>
        <h1>🔧 Debug Data Neraca Lajur</h1>
        <a href="/neraca-lajur">← Kembali ke Neraca Lajur</a>
        
        <div class="section">
            <h2>📊 Summary Data</h2>
            <ul>
                <li>Jurnal: {len(jurnal_data)} entri</li>
                <li>Penjualan: {len(penjualan_result.data or [])} transaksi</li>
                <li>Pembelian: {len(pembelian_result.data or [])} transaksi</li>
                <li>Operasional: {len(operasional_result.data or [])} transaksi</li>
                <li>Akun Neraca: {len(neraca_data.get('akun_data', {}))} akun</li>
            </ul>
        </div>
        
        <div class="section">
            <h2>📝 Data Jurnal ({len(jurnal_data)} entri):</h2>
            <pre>{json.dumps(jurnal_data, indent=2, ensure_ascii=False, default=str)}</pre>
        </div>
        
        <div class="section">
            <h2>📊 Data Neraca Lajur:</h2>
            <pre>{json.dumps(neraca_data, indent=2, ensure_ascii=False, default=str)}</pre>
        </div>
        
        <div class="section">
            <h2>🔧 Aksi Cepat</h2>
            <a href="/generate-jurnal-otomatis" style="background: #ff66a3; color: white; padding: 10px; text-decoration: none; border-radius: 5px;">
                🔄 Generate Ulang Semua Jurnal
            </a>
        </div>
    </body>
    </html>
    """
    
    return debug_html

@app.route("/debug-data")
def debug_data():
    """Debug route untuk melihat data sebenarnya di Supabase"""
    if not session.get('logged_in'):
        return redirect('/login')
    
    try:
        # Ambil semua data dari berbagai tabel
        jurnal_data = supabase.table("jurnal_umum").select("*").execute().data or []
        penjualan_data = supabase.table("penjualan").select("*").execute().data or []
        pembelian_data = supabase.table("pembelian").select("*").execute().data or []
        operasional_data = supabase.table("operasional").select("*").execute().data or []
        
        debug_html = f"""
        <html>
        <head><title>Debug Data</title></head>
        <body style="font-family: Arial; padding: 20px;">
            <h1>🔧 Debug Data Supabase</h1>
            <a href="/neraca-lajur">← Kembali ke Neraca Lajur</a>
            
            <h2>📊 Summary Data</h2>
            <ul>
                <li>Jurnal Umum: {len(jurnal_data)} entri</li>
                <li>Penjualan: {len(penjualan_data)} transaksi</li>
                <li>Pembelian: {len(pembelian_data)} transaksi</li>
                <li>Operasional: {len(operasional_data)} transaksi</li>
            </ul>
            
            <h2>📝 Data Jurnal Umum</h2>
            <table border="1" style="border-collapse: collapse; width: 100%;">
                <tr>
                    <th>ID</th><th>Tanggal</th><th>Akun</th><th>Debit</th><th>Kredit</th><th>Type</th>
                </tr>
                {"".join([f"""
                <tr>
                    <td>{j.get('id')}</td>
                    <td>{j.get('tanggal')}</td>
                    <td>{j.get('nama_akun')}</td>
                    <td>{j.get('debit')}</td>
                    <td>{j.get('kredit')}</td>
                    <td>{j.get('transaksi_type')}</td>
                </tr>
                """ for j in jurnal_data])}
            </table>
            
            <h2>🔧 Quick Fix</h2>
            <a href="/generate-jurnal-otomatis" style="background: #ff66a3; color: white; padding: 10px; text-decoration: none; border-radius: 5px;">
                🔄 Generate Ulang Jurnal dari Transaksi
            </a>
        </body>
        </html>
        """
        return debug_html
        
    except Exception as e:
        return f"Error: {str(e)}"

def hitung_laba_bersih():
    """Hitung laba bersih langsung dari database"""
    try:
        # Ambil semua data jurnal
        jurnal_data = supabase.table("jurnal_umum").select("*").execute().data or []
        
        total_pendapatan = 0
        total_beban = 0
        
        for jurnal in jurnal_data:
            akun_nama = jurnal.get('nama_akun', '').lower()
            
            # Klasifikasi akun pendapatan dan beban
            if any(keyword in akun_nama for keyword in ['pendapatan', 'penjualan', 'jasa']):
                total_pendapatan += jurnal.get('kredit', 0) - jurnal.get('debit', 0)
            elif any(keyword in akun_nama for keyword in ['beban', 'hpp', 'biaya', 'gaji', 'listrik', 'pakan', 'obat']):
                total_beban += jurnal.get('debit', 0) - jurnal.get('kredit', 0)
        
        laba_bersih = total_pendapatan - total_beban
        return laba_bersih
        
    except Exception as e:
        logger.error(f"Error hitung laba bersih: {str(e)}")
        return 0

# ============================================================
# 🔹 FUNGSI BANTUAN NERACA LAJUR 
# ============================================================

def get_neraca_lajur_simple():
    
    try:
        # Ambil semua data jurnal
        jurnal_result = supabase.table("jurnal_umum").select("*").order("tanggal").execute()
        jurnal_data = jurnal_result.data or []
        
        # Kelompokkan per akun
        akun_data = {}
        
        for jurnal in jurnal_data:
            akun_nama = jurnal.get('nama_akun', 'Unknown')
            debit = float(jurnal.get('debit', 0) or 0)
            kredit = float(jurnal.get('kredit', 0) or 0)
            
            if akun_nama not in akun_data:
                akun_data[akun_nama] = {
                    'neraca_debit': 0,
                    'neraca_kredit': 0,
                    'penyesuaian_debit': 0,
                    'penyesuaian_kredit': 0,
                    'nssp_debit': 0,
                    'nssp_kredit': 0
                }
            
            # Pisahkan antara jurnal biasa dan jurnal penyesuaian
            if jurnal.get('transaksi_type') == 'PENYESUAIAN':
                # Jurnal penyesuaian
                akun_data[akun_nama]['penyesuaian_debit'] += debit
                akun_data[akun_nama]['penyesuaian_kredit'] += kredit
            else:
                # Jurnal biasa (neraca saldo)
                akun_data[akun_nama]['neraca_debit'] += debit
                akun_data[akun_nama]['neraca_kredit'] += kredit
        
        # Hitung Neraca Saldo Setelah Penyesuaian (NSSP)
        for akun_nama, data in akun_data.items():
            data['nssp_debit'] = data['neraca_debit'] + data['penyesuaian_debit']
            data['nssp_kredit'] = data['neraca_kredit'] + data['penyesuaian_kredit']
        
        return {
            'akun_data': akun_data,
            'total_jurnal': len(jurnal_data),
            'total_akun': len(akun_data)
        }
        
    except Exception as e:
        logger.error(f"❌ Error di get_neraca_lajur_simple: {str(e)}")
        return None

def get_neraca_lajur():
    
    try:
        # Ambil semua data jurnal
        jurnal_result = supabase.table("jurnal_umum").select("*").order("tanggal").execute()
        jurnal_data = jurnal_result.data or []
        
        # Kelompokkan per akun
        akun_data = {}
        
        for jurnal in jurnal_data:
            akun_nama = jurnal.get('nama_akun', 'Unknown')
            debit = float(jurnal.get('debit', 0) or 0)
            kredit = float(jurnal.get('kredit', 0) or 0)
            
            if akun_nama not in akun_data:
                akun_data[akun_nama] = {
                    # Kolom 1-2: Neraca Saldo
                    'neraca_debit': 0,
                    'neraca_kredit': 0,
                    # Kolom 3-4: Penyesuaian
                    'penyesuaian_debit': 0,
                    'penyesuaian_kredit': 0,
                    # Kolom 5-6: Neraca Saldo Setelah Penyesuaian
                    'nssp_debit': 0,
                    'nssp_kredit': 0,
                    # Kolom 7-8: Laporan Laba Rugi
                    'laba_rugi_debit': 0,
                    'laba_rugi_kredit': 0,
                    # Kolom 9-10: Posisi Keuangan (Neraca)
                    'posisi_keuangan_debit': 0,
                    'posisi_keuangan_kredit': 0
                }
            
            # Pisahkan antara jurnal biasa dan jurnal penyesuaian
            if jurnal.get('transaksi_type') == 'PENYESUAIAN':
                akun_data[akun_nama]['penyesuaian_debit'] += debit
                akun_data[akun_nama]['penyesuaian_kredit'] += kredit
            else:
                akun_data[akun_nama]['neraca_debit'] += debit
                akun_data[akun_nama]['neraca_kredit'] += kredit
        
        # Hitung Neraca Saldo Setelah Penyesuaian (NSSP)
        for akun_nama, data in akun_data.items():
            data['nssp_debit'] = data['neraca_debit'] + data['penyesuaian_debit']
            data['nssp_kredit'] = data['neraca_kredit'] + data['penyesuaian_kredit']
            
            saldo_nssp = data['nssp_debit'] - data['nssp_kredit']
            akun_lower = akun_nama.lower()
            
            # 1. AKUN NOMINAL (Laba Rugi) - periode berjalan
            if any(keyword in akun_lower for keyword in ['pendapatan', 'penjualan', 'jasa', 'hasil']):
                # Pendapatan: hanya di Kredit Laba Rugi (saldo kredit)
                if saldo_nssp < 0:  # Saldo kredit (normal)
                    data['laba_rugi_debit'] = 0
                    data['laba_rugi_kredit'] = abs(saldo_nssp)
                else:  # Saldo debit (tidak normal)
                    data['laba_rugi_debit'] = saldo_nssp
                    data['laba_rugi_kredit'] = 0
                data['posisi_keuangan_debit'] = 0
                data['posisi_keuangan_kredit'] = 0
                
            elif any(keyword in akun_lower for keyword in ['beban', 'biaya', 'hpp', 'gaji', 'listrik', 'air', 'telepon', 'sewa', 'pajak']):
                # Beban: hanya di Debit Laba Rugi (saldo debit)
                if saldo_nssp > 0:  # Saldo debit (normal)
                    data['laba_rugi_debit'] = saldo_nssp
                    data['laba_rugi_kredit'] = 0
                else:  # Saldo kredit (tidak normal)
                    data['laba_rugi_debit'] = 0
                    data['laba_rugi_kredit'] = abs(saldo_nssp)
                data['posisi_keuangan_debit'] = 0
                data['posisi_keuangan_kredit'] = 0
            
            # 2. AKUN RIIL (Posisi Keuangan) - permanen
            elif any(keyword in akun_lower for keyword in ['kas', 'bank', 'piutang', 'persediaan', 'peralatan', 'tanah', 'bangunan', 'kendaraan', 'aset']):
                # Aset: hanya di Debit Posisi Keuangan
                data['laba_rugi_debit'] = 0
                data['laba_rugi_kredit'] = 0
                if saldo_nssp > 0:  # Saldo debit (normal untuk aset)
                    data['posisi_keuangan_debit'] = saldo_nssp
                    data['posisi_keuangan_kredit'] = 0
                else:  # Saldo kredit (tidak normal untuk aset)
                    data['posisi_keuangan_debit'] = 0
                    data['posisi_keuangan_kredit'] = abs(saldo_nssp)
                
            elif any(keyword in akun_lower for keyword in ['utang', 'hutang', 'kewajiban']):
                # Utang: hanya di Kredit Posisi Keuangan
                data['laba_rugi_debit'] = 0
                data['laba_rugi_kredit'] = 0
                if saldo_nssp < 0:  # Saldo kredit (normal untuk utang)
                    data['posisi_keuangan_debit'] = 0
                    data['posisi_keuangan_kredit'] = abs(saldo_nssp)
                else:  # Saldo debit (tidak normal untuk utang)
                    data['posisi_keuangan_debit'] = saldo_nssp
                    data['posisi_keuangan_kredit'] = 0
                    
            elif any(keyword in akun_lower for keyword in ['modal', 'prive', 'ekuitas']):
                # Modal: hanya di Kredit Posisi Keuangan
                # Prive: hanya di Debit Posisi Keuangan
                data['laba_rugi_debit'] = 0
                data['laba_rugi_kredit'] = 0
                if 'prive' in akun_lower:
                    # Prive: debit (pengurangan modal)
                    data['posisi_keuangan_debit'] = abs(saldo_nssp) if saldo_nssp != 0 else 0
                    data['posisi_keuangan_kredit'] = 0
                else:
                    # Modal: kredit
                    data['posisi_keuangan_debit'] = 0
                    data['posisi_keuangan_kredit'] = abs(saldo_nssp) if saldo_nssp != 0 else 0
            
            else:
                # Default: asumsikan akun neraca (posisi keuangan)
                data['laba_rugi_debit'] = 0
                data['laba_rugi_kredit'] = 0
                if saldo_nssp > 0:
                    data['posisi_keuangan_debit'] = saldo_nssp
                    data['posisi_keuangan_kredit'] = 0
                else:
                    data['posisi_keuangan_debit'] = 0
                    data['posisi_keuangan_kredit'] = abs(saldo_nssp)
        
        # Hitung totals
        totals = {
            'neraca_debit': 0, 'neraca_kredit': 0,
            'penyesuaian_debit': 0, 'penyesuaian_kredit': 0,
            'nssp_debit': 0, 'nssp_kredit': 0,
            'laba_rugi_debit': 0, 'laba_rugi_kredit': 0,
            'posisi_keuangan_debit': 0, 'posisi_keuangan_kredit': 0
        }
        
        for data in akun_data.values():
            for key in totals:
                totals[key] += data.get(key, 0)
        
        # PERHITUNGAN KESEIMBANGAN 
        neraca_saldo_balance = abs(totals['neraca_debit'] - totals['neraca_kredit']) < 0.01
        nssp_balance = abs(totals['nssp_debit'] - totals['nssp_kredit']) < 0.01
        
        # Keseimbangan akhir: Laba Rugi = Selisih Posisi Keuangan
        total_laba_rugi_debit = totals['laba_rugi_debit']
        total_laba_rugi_kredit = totals['laba_rugi_kredit']
        total_posisi_debit = totals['posisi_keuangan_debit']
        total_posisi_kredit = totals['posisi_keuangan_kredit']
        
        # Laba/Rugi = Pendapatan - Beban
        laba_rugi = total_laba_rugi_kredit - total_laba_rugi_debit
        
        # Dalam neraca lajur yang balance: Total Debit Posisi Keuangan + Total Debit Laba Rugi = Total Kredit Posisi Keuangan + Total Kredit Laba Rugi
        total_debit_all = total_laba_rugi_debit + total_posisi_debit
        total_kredit_all = total_laba_rugi_kredit + total_posisi_kredit
        final_balance = abs(total_debit_all - total_kredit_all) < 0.01
        
        is_balanced = neraca_saldo_balance and nssp_balance and final_balance
        
        return {
            'akun_data': akun_data,
            'total_jurnal': len(jurnal_data),
            'total_akun': len(akun_data),
            'totals': totals,
            'laba_rugi': laba_rugi,
            'is_balanced': is_balanced,
            'debug_info': {
                'total_laba_rugi_debit': total_laba_rugi_debit,
                'total_laba_rugi_kredit': total_laba_rugi_kredit,
                'total_posisi_debit': total_posisi_debit,
                'total_posisi_kredit': total_posisi_kredit,
                'total_debit_all': total_debit_all,
                'total_kredit_all': total_kredit_all
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error di get_neraca_lajur: {str(e)}")
        import traceback
        logger.error(f"🔍 Traceback: {traceback.format_exc()}")
        return None
            
# ============================================================
# 🔹 ROUTE: Laporan Arus Kas 
# ============================================================
@app.route("/arus-kas")
def arus_kas():
    if not session.get('logged_in'):
        return redirect('/login')
    
    user_email = session.get('user_email')
    
    try:
        # Ambil data arus kas dari semua transaksi
        arus_kas_data = hitung_arus_kas_otomatis()
        
        # Format currency helper
        def rp(amount):
            return f"Rp {int(amount):,}".replace(",", ".")
        
        # Generate HTML sections
        aktivitas_operasi = generate_aktivitas_operasi(arus_kas_data, rp)
        aktivitas_investasi = generate_aktivitas_investasi(arus_kas_data, rp)
        aktivitas_pendanaan = generate_aktivitas_pendanaan(arus_kas_data, rp)
        ringkasan_arus_kas = generate_ringkasan_arus_kas(arus_kas_data, rp)
        grafik_arus_kas = generate_grafik_arus_kas(arus_kas_data, rp)
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Laporan Arus Kas - PINKILANG</title>
            <meta charset="utf-8">
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}
                
                body {{
                    font-family: 'Arial', sans-serif;
                    background: linear-gradient(135deg, #e6f7ff, #f0f8ff);
                    padding: 20px;
                    min-height: 100vh;
                }}
                
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 15px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                    overflow: hidden;
                }}
                
                .header {{
                    background: linear-gradient(135deg, #66b3ff, #4d94ff);
                    color: white;
                    padding: 25px;
                    text-align: center;
                }}
                
                .back-btn {{
                    display: inline-block;
                    padding: 10px 20px;
                    background: rgba(255,255,255,0.2);
                    color: white;
                    text-decoration: none;
                    border-radius: 8px;
                    margin-bottom: 15px;
                    border: 1px solid rgba(255,255,255,0.3);
                }}
                
                .back-btn:hover {{
                    background: rgba(255,255,255,0.3);
                }}
                
                h1 {{
                    font-size: 28px;
                    margin-bottom: 10px;
                }}
                
                .content {{
                    padding: 25px;
                }}
                
                .section {{
                    margin: 25px 0;
                    padding: 20px;
                    background: #f8fbff;
                    border-radius: 12px;
                    border-left: 5px solid #66b3ff;
                }}
                
                .section-title {{
                    color: #66b3ff;
                    font-size: 22px;
                    margin-bottom: 20px;
                    padding-bottom: 10px;
                    border-bottom: 2px solid #e6f2ff;
                }}
                
                .calculation-table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 15px 0;
                    background: white;
                    border-radius: 8px;
                    overflow: hidden;
                    box-shadow: 0 4px 15px rgba(102,179,255,0.1);
                }}
                
                .calculation-table th {{
                    background: #66b3ff;
                    color: white;
                    padding: 12px;
                    text-align: left;
                    font-weight: bold;
                }}
                
                .calculation-table td {{
                    padding: 12px;
                    border-bottom: 1px solid #e6f2ff;
                }}
                
                .calculation-table tr:hover {{
                    background: #f0f8ff;
                }}
                
                .number {{
                    text-align: right;
                    font-family: 'Courier New', monospace;
                    font-weight: bold;
                }}
                
                .positive {{
                    color: #00cc66;
                }}
                
                .negative {{
                    color: #ff6666;
                }}
                
                .total-row {{
                    background: #e6f2ff;
                    font-weight: bold;
                    font-size: 16px;
                }}
                
                .subtotal-row {{
                    background: #f0f8ff;
                    font-weight: bold;
                }}
                
                .info-box {{
                    background: #e6f7ff;
                    border: 1px solid #91d5ff;
                    border-radius: 8px;
                    padding: 15px;
                    margin: 15px 0;
                    color: #0066cc;
                }}
                
                .stats-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 15px;
                    margin: 20px 0;
                }}
                
                .stat-card {{
                    background: white;
                    padding: 20px;
                    border-radius: 10px;
                    text-align: center;
                    box-shadow: 0 4px 15px rgba(102,179,255,0.1);
                    border: 1px solid #e6f2ff;
                }}
                
                .stat-number {{
                    font-size: 24px;
                    font-weight: bold;
                    color: #66b3ff;
                    margin: 10px 0;
                }}
                
                .stat-label {{
                    color: #3399ff;
                    font-size: 14px;
                    font-weight: bold;
                }}
                
                .chart-container {{
                    background: white;
                    padding: 20px;
                    border-radius: 10px;
                    margin: 20px 0;
                    box-shadow: 0 4px 15px rgba(102,179,255,0.1);
                }}
                
                .chart-bar {{
                    display: flex;
                    align-items: center;
                    margin: 15px 0;
                }}
                
                .chart-label {{
                    width: 150px;
                    font-weight: bold;
                    color: #333;
                }}
                
                .chart-bar-inner {{
                    flex: 1;
                    background: #e6f2ff;
                    border-radius: 10px;
                    height: 30px;
                    margin: 0 15px;
                    overflow: hidden;
                }}
                
                .chart-bar-fill {{
                    height: 100%;
                    border-radius: 10px;
                    transition: width 0.5s ease;
                }}
                
                .chart-value {{
                    width: 100px;
                    text-align: right;
                    font-weight: bold;
                    font-family: 'Courier New', monospace;
                }}
                
                .btn {{
                    display: inline-block;
                    padding: 10px 20px;
                    background: #66b3ff;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    margin: 5px;
                }}
                
                .btn:hover {{
                    background: #4d94ff;
                }}
                
                .period-selector {{
                    background: white;
                    padding: 15px;
                    border-radius: 8px;
                    margin: 15px 0;
                    text-align: center;
                }}
                
                .empty-state {{
                    text-align: center;
                    padding: 40px;
                    color: #999;
                    font-style: italic;
                }}
                
                .cash-flow-positive {{
                    background: #f0fff0;
                    border-left: 5px solid #00cc66;
                }}
                
                .cash-flow-negative {{
                    background: #fff0f0;
                    border-left: 5px solid #ff6666;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <!-- Header -->
                <div class="header">
                    <a href="/dashboard" class="back-btn">← Kembali ke Dashboard</a>
                    <h1>💧 Laporan Arus Kas</h1>
                    <p>Terintegrasi Otomatis dengan Semua Transaksi - PINKILANG</p>
                </div>
                
                <!-- Content -->
                <div class="content">
                    <!-- Ringkasan Arus Kas -->
                    {ringkasan_arus_kas}
                    
                    <!-- Aktivitas Operasi -->
                    {aktivitas_operasi}
                    
                    <!-- Aktivitas Investasi -->
                    {aktivitas_investasi}
                    
                    <!-- Aktivitas Pendanaan -->
                    {aktivitas_pendanaan}
                    
                    <!-- Grafik Arus Kas -->
                    {grafik_arus_kas}
                    
                    <!-- Action Buttons -->
                    <div style="text-align: center; margin-top: 30px;">
                        <a href="/jurnal-umum" class="btn">📝 Lihat Jurnal</a>
                        <a href="/laba-rugi" class="btn">📊 Lihat Laba Rugi</a>
                        <a href="/neraca" class="btn">🏦 Lihat Neraca</a>
                        <button onclick="window.print()" class="btn">🖨️ Cetak Laporan</button>
                    </div>
                    
                </div>
            </div>
                
                // Animate chart bars
                document.addEventListener('DOMContentLoaded', function() {{
                    const bars = document.querySelectorAll('.chart-bar-fill');
                    bars.forEach(bar => {{
                        const targetWidth = bar.style.width;
                        bar.style.width = '0%';
                        setTimeout(() => {{
                            bar.style.width = targetWidth;
                        }}, 100);
                    }});
                }});
            </script>
        </body>
        </html>
        """
        return html 
        
    except Exception as e:
        logger.error(f"❌ Error di laporan arus kas: {str(e)}")
        return create_error_page("Arus Kas", str(e))

def hitung_arus_kas_otomatis():
    """Hitung arus kas otomatis dari semua transaksi jurnal"""
    try:
        # Ambil semua data jurnal yang mempengaruhi kas
        jurnal_result = supabase.table("jurnal_umum").select("*").execute()
        jurnal_data = jurnal_result.data or []
        
        logger.info(f"📊 Memproses {len(jurnal_data)} entri jurnal untuk arus kas")
        
        # Inisialisasi variabel
        arus_kas_data = {
            # Aktivitas Operasi
            'penerimaan_kas': {
                'penjualan_tunai': 0,
                'penerimaan_piutang': 0,
                'pendapatan_jasa': 0,
                'lainnya_operasi': 0
            },
            'pengeluaran_operasi': {
                'pembelian_tunai': 0,
                'beban_operasional': 0,
                'beban_gaji': 0,
                'beban_listrik': 0,
                'beban_lainnya': 0
            },
            
            # Aktivitas Investasi
            'pembelian_aset': 0,
            'penjualan_aset': 0,
            'investasi_lainnya': 0,
            
            # Aktivitas Pendanaan
            'tambahan_modal': 0,
            'prive': 0,
            'pinjaman': 0,
            'pelunasan_pinjaman': 0
        }
        
        # Proses setiap entri jurnal
        for jurnal in jurnal_data:
            nama_akun = jurnal.get('nama_akun', '').lower()
            debit = float(jurnal.get('debit', 0) or 0)
            kredit = float(jurnal.get('kredit', 0) or 0)
            deskripsi = jurnal.get('deskripsi', '').lower()
            transaksi_type = jurnal.get('transaksi_type', '')
            
            # 🔍 IDENTIFIKASI TRANSAKSI KAS
            if 'kas' in nama_akun:
                # Kas bertambah (debit) = penerimaan kas
                # Kas berkurang (kredit) = pengeluaran kas
                
                # 🎯 AKTIVITAS OPERASI
                if any(keyword in deskripsi for keyword in ['penjualan', 'jual', 'pendapatan']):
                    if debit > 0:  # Penerimaan kas dari penjualan
                        arus_kas_data['penerimaan_kas']['penjualan_tunai'] += debit
                
                elif any(keyword in deskripsi for keyword in ['piutang', 'pelunasan']):
                    if debit > 0:  # Penerimaan piutang
                        arus_kas_data['penerimaan_kas']['penerimaan_piutang'] += debit
                
                elif any(keyword in deskripsi for keyword in ['jasa', 'service']):
                    if debit > 0:  # Pendapatan jasa
                        arus_kas_data['penerimaan_kas']['pendapatan_jasa'] += debit
                
                elif any(keyword in deskripsi for keyword in ['pembelian', 'beli']):
                    if kredit > 0:  # Pengeluaran untuk pembelian
                        arus_kas_data['pengeluaran_operasi']['pembelian_tunai'] += kredit
                
                elif any(keyword in deskripsi for keyword in ['beban', 'biaya']):
                    if kredit > 0:  # Pengeluaran beban
                        if 'gaji' in deskripsi:
                            arus_kas_data['pengeluaran_operasi']['beban_gaji'] += kredit
                        elif any(keyword in deskripsi for keyword in ['listrik', 'air', 'telepon']):
                            arus_kas_data['pengeluaran_operasi']['beban_listrik'] += kredit
                        else:
                            arus_kas_data['pengeluaran_operasi']['beban_operasional'] += kredit
                
                # 🎯 AKTIVITAS INVESTASI
                elif any(keyword in deskripsi for keyword in ['aset', 'peralatan', 'kendaraan', 'bangunan']):
                    if kredit > 0:  # Pembelian aset
                        arus_kas_data['pembelian_aset'] += kredit
                    elif debit > 0:  # Penjualan aset
                        arus_kas_data['penjualan_aset'] += debit
                
                # 🎯 AKTIVITAS PENDANAAN  
                elif any(keyword in deskripsi for keyword in ['modal', 'tambahan modal']):
                    if debit > 0:  # Tambahan modal
                        arus_kas_data['tambahan_modal'] += debit
                
                elif 'prive' in deskripsi:
                    if kredit > 0:  # Pengambilan prive
                        arus_kas_data['prive'] += kredit
                
                elif any(keyword in deskripsi for keyword in ['pinjaman', 'hutang', 'utang']):
                    if debit > 0:  # Penerimaan pinjaman
                        arus_kas_data['pinjaman'] += debit
                    elif kredit > 0:  # Pelunasan pinjaman
                        arus_kas_data['pelunasan_pinjaman'] += kredit
        
        # Hitung totals
        total_penerimaan_operasi = sum(arus_kas_data['penerimaan_kas'].values())
        total_pengeluaran_operasi = sum(arus_kas_data['pengeluaran_operasi'].values())
        arus_kas_operasi = total_penerimaan_operasi - total_pengeluaran_operasi
        
        arus_kas_investasi = arus_kas_data['penjualan_aset'] - arus_kas_data['pembelian_aset'] + arus_kas_data['investasi_lainnya']
        
        arus_kas_pendanaan = arus_kas_data['tambahan_modal'] + arus_kas_data['pinjaman'] - arus_kas_data['prive'] - arus_kas_data['pelunasan_pinjaman']
        
        kenaikan_bersih_kas = arus_kas_operasi + arus_kas_investasi + arus_kas_pendanaan
        
        # Saldo kas awal (asumsi)
        saldo_kas_awal = 15000000  # Rp 15.000.000
        saldo_kas_akhir = saldo_kas_awal + kenaikan_bersih_kas
        
        logger.info(f"📊 Ringkasan Arus Kas:")
        logger.info(f"   Operasi: {arus_kas_operasi}")
        logger.info(f"   Investasi: {arus_kas_investasi}") 
        logger.info(f"   Pendanaan: {arus_kas_pendanaan}")
        logger.info(f"   Kenaikan Bersih: {kenaikan_bersih_kas}")
        
        return {
            **arus_kas_data,
            'total_penerimaan_operasi': total_penerimaan_operasi,
            'total_pengeluaran_operasi': total_pengeluaran_operasi,
            'arus_kas_operasi': arus_kas_operasi,
            'arus_kas_investasi': arus_kas_investasi,
            'arus_kas_pendanaan': arus_kas_pendanaan,
            'kenaikan_bersih_kas': kenaikan_bersih_kas,
            'saldo_kas_awal': saldo_kas_awal,
            'saldo_kas_akhir': saldo_kas_akhir,
            'jurnal_diproses': len(jurnal_data)
        }
        
    except Exception as e:
        logger.error(f"❌ Error hitung_arus_kas_otomatis: {str(e)}")
        import traceback
        logger.error(f"🔍 Traceback: {traceback.format_exc()}")
        return {}

def generate_aktivitas_operasi(arus_kas_data, rp_func):
    """Generate HTML section untuk aktivitas operasi"""
    
    penerimaan_items = ""
    for item, nilai in arus_kas_data['penerimaan_kas'].items():
        if nilai > 0:
            penerimaan_items += f"""
            <tr>
                <td style="padding-left: 20px;">{item.replace('_', ' ').title()}</td>
                <td class="number positive">+ {rp_func(nilai)}</td>
            </tr>
            """
    
    pengeluaran_items = ""
    for item, nilai in arus_kas_data['pengeluaran_operasi'].items():
        if nilai > 0:
            pengeluaran_items += f"""
            <tr>
                <td style="padding-left: 20px;">{item.replace('_', ' ').title()}</td>
                <td class="number negative">- {rp_func(nilai)}</td>
            </tr>
            """
    
    return f"""
    <div class="section">
        <h2 class="section-title">🏢 Aktivitas Operasi</h2>
        <p>Arus kas dari aktivitas operasi utama perusahaan</p>
        
        <table class="calculation-table">
            <thead>
                <tr>
                    <th>Penerimaan Kas dari Operasi</th>
                    <th>Jumlah</th>
                </tr>
            </thead>
            <tbody>
                {penerimaan_items if penerimaan_items.strip() else '''
                <tr>
                    <td colspan="2" style="text-align: center; color: #999;">
                        Belum ada penerimaan kas dari operasi
                    </td>
                </tr>
                '''}
                <tr class="subtotal-row">
                    <td><strong>Total Penerimaan Operasi</strong></td>
                    <td class="number positive"><strong>+ {rp_func(arus_kas_data['total_penerimaan_operasi'])}</strong></td>
                </tr>
            </tbody>
        </table>
        
        <table class="calculation-table" style="margin-top: 20px;">
            <thead>
                <tr>
                    <th>Pengeluaran Kas untuk Operasi</th>
                    <th>Jumlah</th>
                </tr>
            </thead>
            <tbody>
                {pengeluaran_items if pengeluaran_items.strip() else '''
                <tr>
                    <td colspan="2" style="text-align: center; color: #999;">
                        Belum ada pengeluaran kas untuk operasi
                    </td>
                </tr>
                '''}
                <tr class="subtotal-row">
                    <td><strong>Total Pengeluaran Operasi</strong></td>
                    <td class="number negative"><strong>- {rp_func(arus_kas_data['total_pengeluaran_operasi'])}</strong></td>
                </tr>
            </tbody>
        </table>
        
        <div class="total-row" style="padding: 15px; background: #e6f2ff; border-radius: 8px; margin-top: 15px;">
            <table style="width: 100%;">
                <tr>
                    <td><strong>ARUS KAS BERSIH DARI AKTIVITAS OPERASI</strong></td>
                    <td class="number {'positive' if arus_kas_data['arus_kas_operasi'] >= 0 else 'negative'}">
                        <strong>{rp_func(arus_kas_data['arus_kas_operasi'])}</strong>
                    </td>
                </tr>
            </table>
        </div>
    </div>
    """

def generate_aktivitas_investasi(arus_kas_data, rp_func):
    """Generate HTML section untuk aktivitas investasi"""
    
    investasi_items = ""
    if arus_kas_data['penjualan_aset'] > 0:
        investasi_items += f"""
        <tr>
            <td style="padding-left: 20px;">Penjualan Aset Tetap</td>
            <td class="number positive">+ {rp_func(arus_kas_data['penjualan_aset'])}</td>
        </tr>
        """
    
    if arus_kas_data['pembelian_aset'] > 0:
        investasi_items += f"""
        <tr>
            <td style="padding-left: 20px;">Pembelian Aset Tetap</td>
            <td class="number negative">- {rp_func(arus_kas_data['pembelian_aset'])}</td>
        </tr>
        """
    
    return f"""
    <div class="section">
        <h2 class="section-title">🏗️ Aktivitas Investasi</h2>
        <p>Arus kas dari pembelian dan penjualan aset tetap</p>
        
        <table class="calculation-table">
            <thead>
                <tr>
                    <th>Transaksi Investasi</th>
                    <th>Jumlah</th>
                </tr>
            </thead>
            <tbody>
                {investasi_items if investasi_items.strip() else '''
                <tr>
                    <td colspan="2" style="text-align: center; color: #999;">
                        Belum ada transaksi investasi
                    </td>
                </tr>
                '''}
                <tr class="total-row">
                    <td><strong>ARUS KAS BERSIH DARI AKTIVITAS INVESTASI</strong></td>
                    <td class="number {'positive' if arus_kas_data['arus_kas_investasi'] >= 0 else 'negative'}">
                        <strong>{rp_func(arus_kas_data['arus_kas_investasi'])}</strong>
                    </td>
                </tr>
            </tbody>
        </table>
    </div>
    """

def generate_aktivitas_pendanaan(arus_kas_data, rp_func):
    """Generate HTML section untuk aktivitas pendanaan"""
    
    pendanaan_items = ""
    if arus_kas_data['tambahan_modal'] > 0:
        pendanaan_items += f"""
        <tr>
            <td style="padding-left: 20px;">Tambahan Modal</td>
            <td class="number positive">+ {rp_func(arus_kas_data['tambahan_modal'])}</td>
        </tr>
        """
    
    if arus_kas_data['pinjaman'] > 0:
        pendanaan_items += f"""
        <tr>
            <td style="padding-left: 20px;">Penerimaan Pinjaman</td>
            <td class="number positive">+ {rp_func(arus_kas_data['pinjaman'])}</td>
        </tr>
        """
    
    if arus_kas_data['prive'] > 0:
        pendanaan_items += f"""
        <tr>
            <td style="padding-left: 20px;">Pengambilan Prive</td>
            <td class="number negative">- {rp_func(arus_kas_data['prive'])}</td>
        </tr>
        """
    
    if arus_kas_data['pelunasan_pinjaman'] > 0:
        pendanaan_items += f"""
        <tr>
            <td style="padding-left: 20px;">Pelunasan Pinjaman</td>
            <td class="number negative">- {rp_func(arus_kas_data['pelunasan_pinjaman'])}</td>
        </tr>
        """
    
    return f"""
    <div class="section">
        <h2 class="section-title">💰 Aktivitas Pendanaan</h2>
        <p>Arus kas dari transaksi dengan pemilik dan kreditur</p>
        
        <table class="calculation-table">
            <thead>
                <tr>
                    <th>Transaksi Pendanaan</th>
                    <th>Jumlah</th>
                </tr>
            </thead>
            <tbody>
                {pendanaan_items if pendanaan_items.strip() else '''
                <tr>
                    <td colspan="2" style="text-align: center; color: #999;">
                        Belum ada transaksi pendanaan
                    </td>
                </tr>
                '''}
                <tr class="total-row">
                    <td><strong>ARUS KAS BERSIH DARI AKTIVITAS PENDANAAN</strong></td>
                    <td class="number {'positive' if arus_kas_data['arus_kas_pendanaan'] >= 0 else 'negative'}">
                        <strong>{rp_func(arus_kas_data['arus_kas_pendanaan'])}</strong>
                    </td>
                </tr>
            </tbody>
        </table>
    </div>
    """

def generate_ringkasan_arus_kas(arus_kas_data, rp_func):
    """Generate HTML section untuk ringkasan arus kas"""
    
    is_positive = arus_kas_data['kenaikan_bersih_kas'] >= 0
    
    return f"""
    <div class="section {'cash-flow-positive' if is_positive else 'cash-flow-negative'}">
        <h2 class="section-title" style="color: {'#00cc66' if is_positive else '#ff6666'};">
            📊 Ringkasan Arus Kas
        </h2>
        
        <table class="calculation-table">
            <tbody>
                <tr>
                    <td><strong>Arus Kas dari Aktivitas Operasi</strong></td>
                    <td class="number {'positive' if arus_kas_data['arus_kas_operasi'] >= 0 else 'negative'}">
                        {rp_func(arus_kas_data['arus_kas_operasi'])}
                    </td>
                </tr>
                <tr>
                    <td><strong>Arus Kas dari Aktivitas Investasi</strong></td>
                    <td class="number {'positive' if arus_kas_data['arus_kas_investasi'] >= 0 else 'negative'}">
                        {rp_func(arus_kas_data['arus_kas_investasi'])}
                    </td>
                </tr>
                <tr>
                    <td><strong>Arus Kas dari Aktivitas Pendanaan</strong></td>
                    <td class="number {'positive' if arus_kas_data['arus_kas_pendanaan'] >= 0 else 'negative'}">
                        {rp_func(arus_kas_data['arus_kas_pendanaan'])}
                    </td>
                </tr>
                <tr class="total-row">
                    <td><strong>KENAIKAN (PENURUNAN) BERSIH KAS</strong></td>
                    <td class="number {'positive' if is_positive else 'negative'}">
                        <strong>{rp_func(arus_kas_data['kenaikan_bersih_kas'])}</strong>
                    </td>
                </tr>
                <tr>
                    <td><strong>Saldo Kas Awal Periode</strong></td>
                    <td class="number">{rp_func(arus_kas_data['saldo_kas_awal'])}</td>
                </tr>
                <tr class="total-row">
                    <td><strong>SALDO KAS AKHIR PERIODE</strong></td>
                    <td class="number positive">
                        <strong>{rp_func(arus_kas_data['saldo_kas_akhir'])}</strong>
                    </td>
                </tr>
            </tbody>
        </table>
        
        <div style="text-align: center; margin-top: 15px; padding: 15px; background: {'#d4ffd4' if is_positive else '#ffd4d4'}; border-radius: 8px;">
            <h3 style="color: {'#006600' if is_positive else '#cc0000'};">
                {'💰 KAS BERTAMBAH' if is_positive else '📉 KAS BERKURANG'}
            </h3>
            <p style="color: {'#006600' if is_positive else '#cc0000'}; margin: 5px 0;">
                {f"Kas meningkat sebesar {rp_func(arus_kas_data['kenaikan_bersih_kas'])} selama periode ini" if is_positive else f"Kas berkurang sebesar {rp_func(abs(arus_kas_data['kenaikan_bersih_kas']))} selama periode ini"}
            </p>
        </div>
    </div>
    """

def generate_grafik_arus_kas(arus_kas_data, rp_func):
    """Generate HTML section untuk grafik arus kas"""
    
    # Hitung persentase untuk grafik
    total_absolute = abs(arus_kas_data['arus_kas_operasi']) + abs(arus_kas_data['arus_kas_investasi']) + abs(arus_kas_data['arus_kas_pendanaan'])
    
    if total_absolute > 0:
        pct_operasi = (abs(arus_kas_data['arus_kas_operasi']) / total_absolute) * 100
        pct_investasi = (abs(arus_kas_data['arus_kas_investasi']) / total_absolute) * 100
        pct_pendanaan = (abs(arus_kas_data['arus_kas_pendanaan']) / total_absolute) * 100
    else:
        pct_operasi = pct_investasi = pct_pendanaan = 0
    
    return f"""
    <div class="section">
        <h2 class="section-title">📈 Grafik Komposisi Arus Kas</h2>
        
        <div class="chart-container">
            <h3 style="color: #66b3ff; margin-bottom: 20px;">Distribusi Arus Kas per Aktivitas</h3>
            
            <div class="chart-bar">
                <div class="chart-label">Aktivitas Operasi</div>
                <div class="chart-bar-inner">
                    <div class="chart-bar-fill" style="width: {pct_operasi}%; background: {'#00cc66' if arus_kas_data['arus_kas_operasi'] >= 0 else '#ff6666'};"></div>
                </div>
                <div class="chart-value {'positive' if arus_kas_data['arus_kas_operasi'] >= 0 else 'negative'}">
                    {rp_func(arus_kas_data['arus_kas_operasi'])}
                </div>
            </div>
            
            <div class="chart-bar">
                <div class="chart-label">Aktivitas Investasi</div>
                <div class="chart-bar-inner">
                    <div class="chart-bar-fill" style="width: {pct_investasi}%; background: {'#00cc66' if arus_kas_data['arus_kas_investasi'] >= 0 else '#ff6666'};"></div>
                </div>
                <div class="chart-value {'positive' if arus_kas_data['arus_kas_investasi'] >= 0 else 'negative'}">
                    {rp_func(arus_kas_data['arus_kas_investasi'])}
                </div>
            </div>
            
            <div class="chart-bar">
                <div class="chart-label">Aktivitas Pendanaan</div>
                <div class="chart-bar-inner">
                    <div class="chart-bar-fill" style="width: {pct_pendanaan}%; background: {'#00cc66' if arus_kas_data['arus_kas_pendanaan'] >= 0 else '#ff6666'};"></div>
                </div>
                <div class="chart-value {'positive' if arus_kas_data['arus_kas_pendanaan'] >= 0 else 'negative'}">
                    {rp_func(arus_kas_data['arus_kas_pendanaan'])}
                </div>
            </div>
        </div>
        
        <div style="margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 8px;">
            <h4 style="color: #666; margin-bottom: 10px;">📋 Analisis Arus Kas:</h4>
            <ul style="color: #666;">
                <li><strong>Operasi:</strong> { 'Positif' if arus_kas_data['arus_kas_operasi'] >= 0 else 'Negatif' } - { 'Perusahaan menghasilkan kas dari operasi utama' if arus_kas_data['arus_kas_operasi'] >= 0 else 'Perusahaan menggunakan kas untuk operasi' }</li>
                <li><strong>Investasi:</strong> { 'Positif' if arus_kas_data['arus_kas_investasi'] >= 0 else 'Negatif' } - { 'Perusahaan menjual aset' if arus_kas_data['arus_kas_investasi'] >= 0 else 'Perusahaan berinvestasi dalam aset baru' }</li>
                <li><strong>Pendanaan:</strong> { 'Positif' if arus_kas_data['arus_kas_pendanaan'] >= 0 else 'Negatif' } - { 'Perusahaan mendapatkan pendanaan baru' if arus_kas_data['arus_kas_pendanaan'] >= 0 else 'Perusahaan melunasi kewajiban' }</li>
            </ul>
        </div>
    </div>
    """

# ============================================================
# 🔹 FUNGSI: Hitung Modal dari View
# ============================================================
def hitung_modal_dari_view():
    """Hitung modal awal, tambahan modal, dan prive dari view"""
    modal_awal = 0
    total_tambahan = 0
    total_prive = 0
    
    try:
        if supabase:
            # Ambil data dari view_laporan_modal
            result = supabase.table("view_laporan_modal").select("*").execute()
            
            print(f"🔍 Debug: Found {len(result.data) if result.data else 0} records in view")
            
            if result.data:
                data = result.data[0]  # Ambil record pertama
                
                # Pastikan nama kolom sesuai dengan view
                modal_awal = float(data.get('modal_awal', 0))  # BUKAN 'total_modal_awal'
                total_tambahan = float(data.get('total_tambahan', 0))
                total_prive = float(data.get('total_prive', 0))
                        
    except Exception as e:
        logger.error(f"Error hitung modal dari view: {str(e)}")
        print(f"❌ Error in hitung_modal_dari_view: {str(e)}")
    
    return {
        'modal_awal': modal_awal,
        'total_tambahan': total_tambahan,
        'total_prive': total_prive
    }

# ============================================================
# 🔹 FORM: Input Modal Awal
# ============================================================
@app.route("/input-modal-awal", methods=['GET', 'POST'])
def input_modal_awal():
    if not session.get('logged_in'):
        return redirect('/login')
    
    if request.method == 'POST':
        try:
            jumlah = float(request.form.get('jumlah', 0))
            keterangan = request.form.get('keterangan', 'Saldo Awal Modal')
            tanggal = request.form.get('tanggal', datetime.now().strftime('%Y-%m-%d'))
            
            if jumlah <= 0:
                return '''
                <script>
                    alert("Jumlah harus lebih dari 0!");
                    window.history.back();
                </script>
                '''
            
            # **PERBAIKAN: Konversi ke integer untuk menghindari titik desimal**
            jumlah_int = int(jumlah)  # Konversi ke integer
            
            # Simpan ke tabel modal
            modal_data = {
                'tanggal': tanggal,
                'keterangan': f"Saldo Awal Modal - {keterangan}",
                'tipe': 'MODAL_AWAL',
                'jumlah': jumlah_int,  # **PAKAI INTEGER**
                'user_email': session.get('user_email')
            }
            
            print(f"🔍 Debug: Inserting modal data: {modal_data}")
            
            result = supabase.table("modal").insert(modal_data).execute()
            
            if result.data:
                print("✅ Debug: Modal awal berhasil disimpan")
                return '''
                <script>
                    alert("Modal awal berhasil disimpan!");
                    window.location.href = "/laporan-perubahan-modal";
                </script>
                '''
            else:
                print("❌ Debug: Gagal menyimpan modal awal")
                return '''
                <script>
                    alert("Gagal menyimpan modal awal!");
                    window.history.back();
                </script>
                '''
                
        except Exception as e:
            print(f"❌ Debug: Error: {str(e)}")
            return f'''
            <script>
                alert("Error: {str(e)}");
                window.history.back();
            </script>
            '''
            
    # Form HTML (sama seperti sebelumnya)
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Input Modal Awal - PINKILANG</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { font-family: Arial, sans-serif; background: #fafafa; padding: 20px; }
            .container { background: white; padding: 30px; border-radius: 15px; max-width: 500px; margin: 50px auto; box-shadow: 0 5px 15px rgba(0,0,0,0.1); }
            .form-group { margin-bottom: 20px; }
            label { display: block; margin-bottom: 5px; font-weight: bold; color: #333; }
            input, textarea, select { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; font-size: 16px; }
            button { background: #00cc66; color: white; padding: 12px 30px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; width: 100%; }
            button:hover { background: #00b359; }
            .back-btn { display: inline-block; padding: 10px 20px; background: #666; color: white; text-decoration: none; border-radius: 5px; margin-bottom: 20px; }
        </style>
    </head>
    <body>
        <a href="/laporan-perubahan-modal" class="back-btn">← Kembali</a>
        
        <div class="container">
            <h1>💰 Input Modal Awal</h1>
            <p>Masukkan jumlah modal awal untuk memulai pencatatan keuangan.</p>
            
            <form method="POST">
            <div class="form-group">
                <label>Tanggal:</label>
                <input type="date" name="tanggal" value="''' + datetime.now().strftime('%Y-%m-%d') + '''" required>
            </div>
            
            <div class="form-group">
                <label>Jumlah Modal Awal:</label>
                <!-- **PERBAIKAN: step="any" untuk menerima angka tanpa koma -->
                <input type="number" name="jumlah" placeholder="Contoh: 5000000" min="1" step="any" required>
            </div>
            
            <div class="form-group">
                <label>Keterangan:</label>
                <textarea name="keterangan" placeholder="Contoh: Setoran modal awal usaha" rows="3" required>Saldo Awal Modal</textarea>
            </div>
            
            <button type="submit">💾 Simpan Modal Awal</button>
        </form>
        </div>
    </body>
    </html>
    '''

# ============================================================
# 🔹 FORM: Tambah Modal
# ============================================================
@app.route("/tambah-modal", methods=['GET', 'POST'])
def tambah_modal():
    if not session.get('logged_in'):
        return redirect('/login')
    
    if request.method == 'POST':
        try:
            jumlah = float(request.form.get('jumlah', 0))
            keterangan = request.form.get('keterangan', 'Tambahan Modal')
            tanggal = request.form.get('tanggal', datetime.now().strftime('%Y-%m-%d'))
            
            if jumlah <= 0:
                return "Jumlah harus lebih dari 0"
            
            # 1. Simpan ke tabel modal
            modal_data = {
                'tanggal': tanggal,
                'keterangan': f"Tambahan Modal - {keterangan}",
                'tipe': 'TAMBAHAN_MODAL',
                'jumlah': jumlah,
                'user_email': session.get('user_email')
            }
            
            result_modal = supabase.table("modal").insert(modal_data).execute()
            
            # 2. Simpan ke jurnal umum
            jurnal_data = {
                'tanggal': tanggal,
                'keterangan': f"Tambahan Modal - {keterangan}",
                'akun_debit': 'Kas',
                'akun_kredit': 'Modal',
                'jumlah': jumlah,
                'user_email': session.get('user_email')
            }
            
            result_jurnal = supabase.table("jurnal_umum").insert(jurnal_data).execute()
            
            if result_modal.data and result_jurnal.data:
                return '''
                <script>
                    alert("Tambahan modal berhasil disimpan!");
                    window.location.href = "/laporan-perubahan-modal";
                </script>
                '''
            else:
                return "Gagal menyimpan tambahan modal"
                
        except Exception as e:
            return f"Error: {str(e)}"
    
    # Form HTML (sama seperti sebelumnya)
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Tambah Modal - PINKILANG</title>
        <meta charset="UTF-8">
        <style>
            body { font-family: Arial, sans-serif; background: #fafafa; padding: 20px; }
            .container { background: white; padding: 30px; border-radius: 15px; max-width: 500px; margin: 50px auto; box-shadow: 0 5px 15px rgba(0,0,0,0.1); }
            .form-group { margin-bottom: 20px; }
            label { display: block; margin-bottom: 5px; font-weight: bold; }
            input, textarea { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }
            button { background: #66b3ff; color: white; padding: 12px 30px; border: none; border-radius: 5px; cursor: pointer; width: 100%; }
            .back-btn { display: inline-block; padding: 10px 20px; background: #666; color: white; text-decoration: none; border-radius: 5px; margin-bottom: 20px; }
        </style>
    </head>
    <body>
        <a href="/laporan-perubahan-modal" class="back-btn">← Kembali</a>
        
        <div class="container">
            <h1>➕ Tambah Modal</h1>
            <p>Tambahkan modal baru ke dalam usaha.</p>
            
            <form method="POST">
                <div class="form-group">
                    <label>Tanggal:</label>
                    <input type="date" name="tanggal" value="''' + datetime.now().strftime('%Y-%m-%d') + '''" required>
                </div>
                
                <div class="form-group">
                    <label>Jumlah Tambahan Modal:</label>
                    <input type="number" name="jumlah" placeholder="Contoh: 2000000" min="1" required>
                </div>
                
                <div class="form-group">
                    <label>Keterangan:</label>
                    <textarea name="keterangan" placeholder="Contoh: Setoran modal tambahan" rows="3" required>Tambahan Modal</textarea>
                </div>
                
                <button type="submit">💾 Simpan Tambahan Modal</button>
            </form>
        </div>
    </body>
    </html>
    '''

# ============================================================
# 🔹 FORM: Prive Modal
# ============================================================
@app.route("/prive-modal", methods=['GET', 'POST'])
def prive_modal():
    if not session.get('logged_in'):
        return redirect('/login')
    
    if request.method == 'POST':
        try:
            jumlah = float(request.form.get('jumlah', 0))
            keterangan = request.form.get('keterangan', 'Pengambilan Prive')
            tanggal = request.form.get('tanggal', datetime.now().strftime('%Y-%m-%d'))
            
            if jumlah <= 0:
                return "Jumlah harus lebih dari 0"
            
            # 1. Simpan ke tabel prive
            prive_data = {
                'tanggal': tanggal,
                'keterangan': keterangan,
                'jumlah': jumlah,
                'user_email': session.get('user_email')
            }
            
            result_prive = supabase.table("prive").insert(prive_data).execute()
            
            # 2. Simpan ke jurnal umum
            jurnal_data = {
                'tanggal': tanggal,
                'keterangan': f"Prive - {keterangan}",
                'akun_debit': 'Prive',
                'akun_kredit': 'Kas',
                'jumlah': jumlah,
                'user_email': session.get('user_email')
            }
            
            result_jurnal = supabase.table("jurnal_umum").insert(jurnal_data).execute()
            
            if result_prive.data and result_jurnal.data:
                return '''
                <script>
                    alert("Prive berhasil dicatat!");
                    window.location.href = "/laporan-perubahan-modal";
                </script>
                '''
            else:
                return "Gagal menyimpan prive"
                
        except Exception as e:
            return f"Error: {str(e)}"
    
    # Form HTML (sama seperti sebelumnya)
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Prive Modal - PINKILANG</title>
        <meta charset="UTF-8">
        <style>
            body { font-family: Arial, sans-serif; background: #fafafa; padding: 20px; }
            .container { background: white; padding: 30px; border-radius: 15px; max-width: 500px; margin: 50px auto; box-shadow: 0 5px 15px rgba(0,0,0,0.1); }
            .form-group { margin-bottom: 20px; }
            label { display: block; margin-bottom: 5px; font-weight: bold; }
            input, textarea { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }
            button { background: #ff6666; color: white; padding: 12px 30px; border: none; border-radius: 5px; cursor: pointer; width: 100%; }
            .back-btn { display: inline-block; padding: 10px 20px; background: #666; color: white; text-decoration: none; border-radius: 5px; margin-bottom: 20px; }
        </style>
    </head>
    <body>
        <a href="/laporan-perubahan-modal" class="back-btn">← Kembali</a>
        
        <div class="container">
            <h1>💸 Pengambilan Prive</h1>
            <p>Catat pengambilan dana untuk keperluan pribadi.</p>
            
            <form method="POST">
                <div class="form-group">
                    <label>Tanggal:</label>
                    <input type="date" name="tanggal" value="''' + datetime.now().strftime('%Y-%m-%d') + '''" required>
                </div>
                
                <div class="form-group">
                    <label>Jumlah Prive:</label>
                    <input type="number" name="jumlah" placeholder="Contoh: 500000" min="1" required>
                </div>
                
                <div class="form-group">
                    <label>Keterangan:</label>
                    <textarea name="keterangan" placeholder="Contoh: Pengambilan untuk keperluan pribadi" rows="3" required>Pengambilan Prive</textarea>
                </div>
                
                <button type="submit">💾 Simpan Prive</button>
            </form>
        </div>
    </body>
    </html>
    '''

# ============================================================
# 🔹 ROUTE: Laporan Perubahan Modal - MENGGUNAKAN VIEW
# ============================================================
@app.route("/laporan-perubahan-modal")
def laporan_perubahan_modal():
    if not session.get('logged_in'):
        return redirect('/login')
    
    user_email = session.get('user_email')
    
    try:
        # Hitung modal dari view
        modal_data = hitung_modal_dari_view()
        
        modal_awal = modal_data.get('modal_awal', 0)
        total_tambahan = modal_data.get('total_tambahan', 0)
        total_prive = modal_data.get('total_prive', 0)
        
        # Cek apakah sudah ada modal awal
        sudah_ada_modal_awal = modal_awal > 0
        
        # Hitung laba rugi dari neraca
        try:
            neraca_data = hitung_neraca_terintegrasi()
            laba_bersih = neraca_data.get('laba_bersih', 0)
        except:
            laba_bersih = 0
        
        # Hitung modal akhir
        modal_akhir = modal_awal + total_tambahan - total_prive + laba_bersih
        
        # Format currency helper
        def format_currency(amount):
            try:
                return f"Rp {float(amount):,.0f}".replace(",", ".")
            except:
                return "Rp 0"
        
        # Ambil riwayat transaksi modal dari view
        riwayat_html = ""
        try:
            if supabase:
                result = supabase.table("view_riwayat_modal").select("*").execute()
                
                if result.data:
                    for transaksi in result.data:
                        tanggal = transaksi.get('tanggal', '')
                        keterangan = transaksi.get('keterangan', '')
                        jumlah = float(transaksi.get('jumlah', 0))
                        tipe = transaksi.get('tipe', '')
                        
                        # Tentukan warna berdasarkan tipe
                        if tipe == 'MODAL_AWAL':
                            badge_color = '#00cc66'
                            amount_color = '#00cc66'
                            amount_sign = '+'
                        elif tipe == 'TAMBAHAN_MODAL':
                            badge_color = '#66b3ff'
                            amount_color = '#00cc66'
                            amount_sign = '+'
                        else:  # PRIVE
                            badge_color = '#ff6666'
                            amount_color = '#ff6666'
                            amount_sign = '-'
                        
                        # Format tanggal
                        try:
                            tanggal_formatted = datetime.strptime(str(tanggal), '%Y-%m-%d').strftime('%d/%m/%Y')
                        except:
                            tanggal_formatted = str(tanggal)
                        
                        riwayat_html += f"""
                        <tr style="border-bottom: 1px solid #eee;">
                            <td style="padding: 8px;">{tanggal_formatted}</td>
                            <td style="padding: 8px;">
                                <span style="padding: 4px 8px; border-radius: 12px; font-size: 12px; font-weight: bold; color: white; background: {badge_color}">
                                    {tipe.replace('_', ' ').title()}
                                </span>
                            </td>
                            <td style="padding: 8px;">{keterangan}</td>
                            <td style="padding: 8px; text-align: right; color: {amount_color};">
                                {amount_sign} {format_currency(abs(jumlah))}
                            </td>
                        </tr>
                        """
                
                else:
                    riwayat_html = """
                    <tr>
                        <td colspan="4" style="padding: 20px; text-align: center; color: #999;">
                            Belum ada transaksi modal.
                        </td>
                    </tr>
                    """
                    
        except Exception as e:
            print(f"Error ambil riwayat: {e}")
            riwayat_html = """
            <tr>
                <td colspan="4" style="padding: 20px; text-align: center; color: #999;">
                    Error memuat riwayat transaksi.
                </td>
            </tr>
            """
        
        # Tombol aksi berdasarkan kondisi
        if sudah_ada_modal_awal:
            tombol_modal = '''
            <div class="action-buttons">
                <a href="/tambah-modal" class="action-btn" style="background: #00cc66;">➕ Tambah Modal</a>
                <a href="/prive-modal" class="action-btn" style="background: #66b3ff;">💸 Kelola Prive</a>
                <button onclick="window.print()" class="action-btn" style="background: #ff66a3;">🖨️ Cetak Laporan</button>
            </div>
            '''
            status_modal = '<div style="background: #e6ffe6; padding: 10px; border-radius: 8px; margin: 10px 0; color: #006600;">✅ Modal awal sudah diinput</div>'
        else:
            tombol_modal = '''
            <div class="action-buttons">
                <a href="/input-modal-awal" class="action-btn" style="background: #00cc66;">💰 Input Modal Awal</a>
                <button onclick="window.print()" class="action-btn" style="background: #ff66a3;">🖨️ Cetak Laporan</button>
            </div>
            '''
            status_modal = '<div style="background: #fff0e6; padding: 10px; border-radius: 8px; margin: 10px 0; color: #cc6600;">⚠️ Modal awal belum diinput</div>'
        
        # HTML untuk laporan
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Laporan Perubahan Modal - PINKILANG</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ font-family: Arial, sans-serif; background: #fafafa; padding: 20px; margin: 0; }}
                .container {{ background: white; padding: 30px; border-radius: 15px; max-width: 1000px; margin: 0 auto; box-shadow: 0 5px 15px rgba(0,0,0,0.1); }}
                .header {{ text-align: center; margin-bottom: 30px; padding-bottom: 20px; border-bottom: 2px solid #ff66a3; }}
                .calculation-section {{ margin: 25px 0; padding: 20px; background: #fff5f9; border-radius: 10px; border: 1px solid #ffb6d9; }}
                .calculation-step {{ display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px dashed #ffb6d9; }}
                .calculation-step:last-child {{ border-bottom: none; font-weight: bold; font-size: 18px; color: #ff66a3; margin-top: 10px; padding-top: 15px; border-top: 2px solid #ff66a3; }}
                .back-btn {{ display: inline-block; padding: 10px 20px; background: #666; color: white; text-decoration: none; border-radius: 8px; margin-bottom: 20px; }}
                .action-btn {{ display: inline-block; padding: 12px 25px; color: white; text-decoration: none; border-radius: 8px; margin: 5px; font-weight: bold; }}
                .action-buttons {{ text-align: center; margin: 20px 0; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
                th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #eee; }}
                th {{ background: #ff66a3; color: white; }}
                .debug-info {{ background: #e6f7ff; padding: 10px; border-radius: 8px; margin: 10px 0; font-size: 12px; color: #0066cc; }}
                @media print {{ .back-btn, .action-buttons, .debug-info {{ display: none; }} .container {{ box-shadow: none; padding: 0; }} }}
            </style>
        </head>
        <body>
            <div class="container">
                <a href="/dashboard" class="back-btn">← Kembali ke Dashboard</a>
                
                <div class="header">
                    <h1>📊 Laporan Perubahan Modal</h1>
                    <p>Periode: {datetime.now().strftime('%B %Y')}</p>
                    <p>User: {user_email}</p>
                </div>

                {status_modal}
                
                <!-- Debug Info -->
                <div class="debug-info">
                    <strong>🔍 Debug Info (From View):</strong><br>
                    Modal Awal: {format_currency(modal_awal)} | Tambahan: {format_currency(total_tambahan)} | Prive: {format_currency(total_prive)}<br>
                    Laba Bersih: {format_currency(laba_bersih)} | Modal Akhir: {format_currency(modal_akhir)}
                </div>
                
                {tombol_modal}
                
                <!-- Perhitungan Modal -->
                <div class="calculation-section">
                    <h2>🧮 Perhitungan Modal Akhir</h2>
                    
                    <div class="calculation-step">
                        <span>Modal Awal</span>
                        <span>{format_currency(modal_awal)}</span>
                    </div>
                    
                    <div class="calculation-step">
                        <span>Tambahan Modal</span>
                        <span>+ {format_currency(total_tambahan)}</span>
                    </div>
                    
                    <div class="calculation-step">
                        <span>Prive</span>
                        <span>- {format_currency(total_prive)}</span>
                    </div>
                    
                    <div class="calculation-step">
                        <span>Subtotal Modal</span>
                        <span>{format_currency(modal_awal + total_tambahan - total_prive)}</span>
                    </div>
                    
                    <div class="calculation-step">
                        <span>Laba/Rugi Bersih</span>
                        <span>{format_currency(laba_bersih)}</span>
                    </div>
                    
                    <div class="calculation-step">
                        <span><strong>MODAL AKHIR</strong></span>
                        <span><strong>{format_currency(modal_akhir)}</strong></span>
                    </div>
                </div>
                
                <!-- Riwayat Modal -->
                <div style="margin-top: 30px;">
                    <h3>📋 Riwayat Transaksi Modal</h3>
                    <div style="overflow-x: auto;">
                        <table>
                            <thead>
                                <tr>
                                    <th>Tanggal</th>
                                    <th>Tipe</th>
                                    <th>Keterangan</th>
                                    <th style="text-align: right;">Jumlah</th>
                                </tr>
                            </thead>
                            <tbody>
                                {riwayat_html}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        return html
        
    except Exception as e:
        return f"""
        <html>
        <head><title>Error</title></head>
        <body style="font-family: Arial; padding: 20px;">
            <h1>❌ Error Laporan Perubahan Modal</h1>
            <p><strong>Error:</strong> {str(e)}</p>
            <a href="/dashboard" style="color: blue;">Kembali ke Dashboard</a>
        </body>
        </html>
        """
    
# ============================================================
# 🔹 ROUTE: Prive - DIPERBAIKI untuk integrasi dengan modal
# ============================================================
@app.route("/prive", methods=["GET", "POST"])
def prive():
    if not session.get('logged_in'):
        return redirect('/login')
    
    user_id = session.get('user_id')
    user_email = session.get('user_email')
    message = ""
    
    # Handle form submission untuk prive
    if request.method == "POST" and 'add_prive' in request.form:
        message = process_prive_form(user_id, user_email)
    
    # Handle form submission untuk tambahan modal
    if request.method == "POST" and 'add_tambahan_modal' in request.form:
        message = process_tambahan_modal_form(user_id, user_email)
    
    # Ambil data prive dan modal dari database
    prive_data = get_prive_data()
    modal_data = get_modal_data()
    
    # Hitung totals - DIPERBAIKI: hitung dari modal_data saja untuk konsistensi
    total_prive = sum(item['jumlah'] for item in modal_data if item['tipe'] == 'PRIVE')
    total_tambahan_modal = sum(item['jumlah'] for item in modal_data if item['tipe'] == 'TAMBAHAN_MODAL')
    modal_awal = next((item['jumlah'] for item in modal_data if item['tipe'] == 'MODAL_AWAL'), 0)
    
    # Generate HTML
    return generate_prive_html(
        user_email, 
        message, 
        prive_data, 
        modal_data,
        total_prive,
        total_tambahan_modal,
        modal_awal
    )

def process_prive_form(user_id, user_email):
    """Process prive form submission dengan jurnal otomatis - DIPERBAIKI"""
    try:
        # Collect form data
        tanggal = request.form["tanggal"]
        jumlah = int(request.form["jumlah"])
        keterangan = request.form["keterangan"]
        metode_pembayaran = request.form["metode_pembayaran"]
        
        if jumlah <= 0:
            return '<div class="message error">❌ Jumlah prive harus lebih dari 0!</div>'
        
        # Simpan data prive ke database - DIPERBAIKI: simpan ke tabel modal juga
        prive_data = {
            "user_id": user_id,
            "user_email": user_email,
            "tanggal": tanggal,
            "jumlah": jumlah,
            "keterangan": keterangan,
            "metode_pembayaran": metode_pembayaran,
            "created_at": datetime.now().isoformat()
        }
        
        # Data untuk tabel modal (agar terintegrasi dengan laporan)
        modal_prive_data = {
            "user_id": user_id,
            "user_email": user_email,
            "tanggal": tanggal,
            "jumlah": jumlah,
            "keterangan": f"Prive: {keterangan}",
            "tipe": "PRIVE",  # ✅ Tipe PRIVE untuk integrasi dengan modal
            "sumber_modal": metode_pembayaran,
            "created_at": datetime.now().isoformat()
        }
        
        if supabase:
            # Insert ke tabel prive (untuk backup/data lama)
            insert_result_prive = supabase.table("prive").insert(prive_data).execute()
            
            # Insert ke tabel modal (untuk integrasi dengan laporan)
            insert_result_modal = supabase.table("modal").insert(modal_prive_data).execute()
            
            if insert_result_modal and insert_result_modal.data:
                prive_id = insert_result_modal.data[0]['id']
                
                # ✅ BUAT JURNAL OTOMATIS 
                jurnal_entries = [
                    # Debit: Prive (Pengurangan Modal)
                    {
                        "tanggal": tanggal,
                        "nama_akun": "Prive",
                        "ref": "3120",
                        "debit": jumlah,
                        "kredit": 0,
                        "deskripsi": f"Prive: {keterangan}",
                        "transaksi_type": "PRIVE",
                        "transaksi_id": prive_id,
                        "user_email": user_email,
                        "created_at": datetime.now().isoformat()
                    },
                    # Kredit: Kas/Bank (Pengurangan Kas)
                    {
                        "tanggal": tanggal,
                        "nama_akun": "Kas" if metode_pembayaran == "CASH" else "Bank",
                        "ref": "1110" if metode_pembayaran == "CASH" else "1120",
                        "debit": 0,
                        "kredit": jumlah,
                        "deskripsi": f"Pembayaran prive: {keterangan}",
                        "transaksi_type": "PRIVE",
                        "transaksi_id": prive_id,
                        "user_email": user_email,
                        "created_at": datetime.now().isoformat()
                    }
                ]

                # Simpan jurnal ke database
                success_count = 0
                for entry in jurnal_entries:
                    try:
                        result = supabase.table("jurnal_umum").insert(entry).execute()
                        if result.data:
                            success_count += 1
                            logger.info(f"✅ Jurnal prive: {entry['nama_akun']} - {entry['debit']}/{entry['kredit']}")
                    except Exception as e:
                        logger.error(f"❌ Error insert jurnal prive: {str(e)}")
                
                if success_count == len(jurnal_entries):
                    logger.info(f"✅ Prive berhasil dicatat: {jumlah} oleh {user_email}")
                    return f'<div class="message success">✅ Prive berhasil dicatat! Jurnal otomatis dibuat.</div>'
                else:
                    logger.warning(f"⚠️ Sebagian jurnal prive gagal: {success_count}/{len(jurnal_entries)}")
                    return f'<div class="message success">✅ Prive berhasil dicatat! ({success_count}/{len(jurnal_entries)} jurnal berhasil)</div>'
            else:
                return '<div class="message error">❌ Gagal menyimpan data prive!</div>'
                
    except Exception as e:
        logger.error(f"❌ Error proses prive: {str(e)}")
        return f'<div class="message error">❌ Error mencatat prive: {str(e)}</div>'

def process_tambahan_modal_form(user_id, user_email):
    """Process tambahan modal form submission dengan jurnal otomatis"""
    try:
        # Collect form data
        tanggal = request.form["tanggal_tambahan"]
        jumlah = int(request.form["jumlah_tambahan"])
        keterangan = request.form["keterangan_tambahan"]
        sumber_modal = request.form["sumber_modal"]
        
        if jumlah <= 0:
            return '<div class="message error">❌ Jumlah tambahan modal harus lebih dari 0!</div>'
        
        # Simpan data tambahan modal ke database
        modal_data = {
            "user_id": user_id,
            "user_email": user_email,
            "tanggal": tanggal,
            "jumlah": jumlah,
            "keterangan": f"Tambahan Modal: {keterangan}",
            "sumber_modal": sumber_modal,
            "tipe": "TAMBAHAN_MODAL",
            "created_at": datetime.now().isoformat()
        }
        
        if supabase:
            # Insert ke tabel modal
            insert_result = supabase.table("modal").insert(modal_data).execute()
            
            if insert_result and insert_result.data:
                modal_id = insert_result.data[0]['id']
                
                # ✅ BUAT JURNAL OTOMATIS 
                jurnal_entries = [
                    # Debit: Kas/Bank (Penambahan Kas)
                    {
                        "tanggal": tanggal,
                        "nama_akun": "Kas" if sumber_modal == "CASH" else "Bank",
                        "ref": "1110" if sumber_modal == "CASH" else "1120",
                        "debit": jumlah,
                        "kredit": 0,
                        "deskripsi": f"Tambahan modal: {keterangan}",
                        "transaksi_type": "TAMBAHAN_MODAL",
                        "transaksi_id": modal_id,
                        "user_email": user_email,
                        "created_at": datetime.now().isoformat()
                    },
                    # Kredit: Modal (Penambahan Modal)
                    {
                        "tanggal": tanggal,
                        "nama_akun": "Modal Pemilik",
                        "ref": "3110",
                        "debit": 0,
                        "kredit": jumlah,
                        "deskripsi": f"Tambahan modal: {keterangan}",
                        "transaksi_type": "TAMBAHAN_MODAL",
                        "transaksi_id": modal_id,
                        "user_email": user_email,
                        "created_at": datetime.now().isoformat()
                    }
                ]
                
                # Simpan jurnal ke database
                success_count = 0
                for entry in jurnal_entries:
                    try:
                        result = supabase.table("jurnal_umum").insert(entry).execute()
                        if result.data:
                            success_count += 1
                            logger.info(f"✅ Jurnal tambahan modal: {entry['nama_akun']} - {entry['debit']}/{entry['kredit']}")
                    except Exception as e:
                        logger.error(f"❌ Error insert jurnal tambahan modal: {str(e)}")
                
                if success_count == len(jurnal_entries):
                    logger.info(f"✅ Tambahan modal berhasil dicatat: {jumlah} oleh {user_email}")
                    return f'<div class="message success">✅ Tambahan modal berhasil dicatat! Jurnal otomatis dibuat.</div>'
                else:
                    logger.warning(f"⚠️ Sebagian jurnal tambahan modal gagal: {success_count}/{len(jurnal_entries)}")
                    return f'<div class="message success">✅ Tambahan modal berhasil dicatat! ({success_count}/{len(jurnal_entries)} jurnal berhasil)</div>'
            else:
                return '<div class="message error">❌ Gagal menyimpan data tambahan modal!</div>'
                
    except Exception as e:
        logger.error(f"❌ Error proses tambahan modal: {str(e)}")
        return f'<div class="message error">❌ Error mencatat tambahan modal: {str(e)}</div>'

def get_prive_data():
    """Ambil data prive dari database"""
    try:
        if supabase:
            result = supabase.table("prive").select("*").order("tanggal", desc=True).execute()
            return result.data or []
    except Exception as e:
        logger.error(f"Error ambil data prive: {str(e)}")
    return []

def get_modal_data():
    """Ambil data modal dari database"""
    try:
        if supabase:
            result = supabase.table("modal").select("*").order("tanggal", desc=True).execute()
            return result.data or []
    except Exception as e:
        logger.error(f"Error ambil data modal: {str(e)}")
    return []

def format_currency(amount):
    """Format currency to Indonesian format"""
    return f"Rp {amount:,.0f}".replace(",", ".")

def generate_prive_html(user_email, message, prive_data, modal_data, total_prive, total_tambahan_modal, modal_awal):
    """Generate HTML untuk halaman prive"""
    
    # Generate transaction rows - DIPERBAIKI: ambil prive dari modal_data juga
    prive_rows = generate_prive_rows(prive_data)
    modal_rows = generate_modal_rows(modal_data)
    
    # Hitung modal akhir
    laba_bersih = hitung_laba_bersih()  # Fungsi yang sudah ada
    modal_akhir = modal_awal + total_tambahan_modal - total_prive + laba_bersih

    prive_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Prive & Modal - PINKILANG</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: 'Arial Rounded MT Bold', 'Arial', sans-serif;
                background: linear-gradient(135deg, #ffe6f2, #fff0f7);
                min-height: 100vh;
                padding: 20px;
            }}
            
            .container {{
                max-width: 1400px;
                margin: 0 auto;
                background: white;
                border-radius: 20px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                overflow: hidden;
            }}
            
            .header {{
                background: linear-gradient(135deg, #ff85b3, #ff66a3);
                color: white;
                padding: 30px;
                text-align: center;
            }}
            
            .back-btn {{
                display: inline-block;
                padding: 10px 20px;
                background: rgba(255,255,255,0.2);
                color: white;
                text-decoration: none;
                border-radius: 10px;
                margin-bottom: 20px;
                border: 1px solid rgba(255,255,255,0.3);
            }}
            
            .back-btn:hover {{
                background: rgba(255,255,255,0.3);
            }}
            
            h1 {{
                font-size: 36px;
                margin-bottom: 10px;
            }}
            
            .content {{
                padding: 30px;
            }}
            
            .section {{
                margin-bottom: 40px;
                padding: 25px;
                background: #fff5f9;
                border-radius: 15px;
                border-left: 5px solid #ff85b3;
                box-shadow: 0 4px 15px rgba(255,133,179,0.1);
            }}
            
            .section-title {{
                color: #ff66a3;
                font-size: 24px;
                margin-bottom: 20px;
                padding-bottom: 10px;
                border-bottom: 2px solid #ffe6f2;
            }}
            
            .form-grid {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
                margin-bottom: 20px;
            }}
            
            .form-group {{
                margin-bottom: 15px;
            }}
            
            label {{
                display: block;
                margin-bottom: 5px;
                color: #d63384;
                font-weight: bold;
            }}
            
            input, select, textarea {{
                width: 100%;
                padding: 12px;
                border: 2px solid #ffd1e6;
                border-radius: 10px;
                font-size: 16px;
                transition: border-color 0.3s ease;
                background: white;
            }}
            
            input:focus, select:focus, textarea:focus {{
                border-color: #ff66a3;
                outline: none;
                box-shadow: 0 0 0 3px rgba(255,102,163,0.1);
            }}
            
            .btn {{
                padding: 12px 30px;
                background: linear-gradient(135deg, #ff85b3, #ff66a3);
                color: white;
                border: none;
                border-radius: 10px;
                cursor: pointer;
                font-size: 16px;
                transition: all 0.3s ease;
                font-weight: bold;
            }}
            
            .btn:hover {{
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(255,102,163,0.3);
                background: linear-gradient(135deg, #ff66a3, #ff4d94);
            }}
            
            .btn-secondary {{
                background: linear-gradient(135deg, #66b3ff, #4d94ff);
            }}
            
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin: 20px 0;
            }}
            
            .stat-card {{
                background: white;
                padding: 20px;
                border-radius: 10px;
                text-align: center;
                box-shadow: 0 4px 15px rgba(255,133,179,0.1);
                border: 1px solid #ffe6f2;
                transition: transform 0.3s ease;
            }}
            
            .stat-card:hover {{
                transform: translateY(-5px);
            }}
            
            .stat-number {{
                font-size: 24px;
                font-weight: bold;
                color: #ff66a3;
                margin: 10px 0;
            }}
            
            .stat-label {{
                color: #e83e8c;
                font-size: 14px;
                font-weight: bold;
            }}
            
            .table-container {{
                overflow-x: auto;
                margin-top: 20px;
            }}
            
            table {{
                width: 100%;
                border-collapse: collapse;
                background: white;
                border-radius: 10px;
                overflow: hidden;
                box-shadow: 0 4px 15px rgba(255,133,179,0.1);
            }}
            
            th, td {{
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid #ffe6f2;
                font-size: 14px;
            }}
            
            th {{
                background: linear-gradient(135deg, #ff85b3, #ff66a3);
                color: white;
                font-weight: bold;
            }}
            
            tr:hover {{
                background: #fff5f9;
            }}
            
            .user-badge {{
                background: #ffb6d9;
                color: #c2185b;
                padding: 4px 8px;
                border-radius: 12px;
                font-size: 12px;
                font-weight: bold;
            }}
            
            .current-user {{
                background: #ff66a3;
                color: white;
            }}
            
            .message {{
                padding: 15px;
                margin: 15px 0;
                border-radius: 10px;
                font-size: 14px;
            }}
            
            .success {{
                background: #d4edda;
                color: #155724;
                border: 1px solid #c3e6cb;
            }}
            
            .error {{
                background: #f8d7da;
                color: #721c24;
                border: 1px solid #f5c6cb;
            }}
            
            .info-box {{
                background: #ffe6f2;
                border: 1px solid #ffb6d9;
                border-radius: 10px;
                padding: 15px;
                margin: 15px 0;
                color: #d63384;
            }}
            
            .akun-info {{
                background: #e6f7ff;
                border: 1px solid #b3e0ff;
                border-radius: 8px;
                padding: 10px;
                margin: 5px 0;
                font-size: 12px;
                color: #0066cc;
            }}
            
            .calculation-section {{
                background: #f8f9fa;
                padding: 20px;
                border-radius: 10px;
                margin: 20px 0;
            }}
            
            .calculation-step {{
                display: flex;
                justify-content: space-between;
                padding: 8px 0;
                border-bottom: 1px dashed #dee2e6;
            }}
            
            .calculation-step:last-child {{
                border-bottom: none;
                font-weight: bold;
                font-size: 18px;
                color: #ff66a3;
            }}
            
            .negative {{
                color: #ff6666;
            }}
            
            .positive {{
                color: #00cc66;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <!-- Header -->
            <div class="header">
                <a href="/dashboard" class="back-btn">← Kembali ke Dashboard</a>
                <h1>💼 Modul Prive & Modal</h1>
                <p>Pengelolaan Pengambilan Pribadi dan Tambahan Modal - PINKILANG</p>
                <div style="margin-top: 10px; font-size: 14px; opacity: 0.9;">
                    👋 Login sebagai: <strong>{user_email}</strong>
                </div>
            </div>
            
            <!-- Content -->
            <div class="content">
                {message}
                
                <!-- Ringkasan Modal -->
                <div class="section">
                    <h2 class="section-title">📊 Ringkasan Modal</h2>
                    <div class="stats-grid">
                        <div class="stat-card">
                            <div>💰</div>
                            <div class="stat-number">{format_currency(modal_awal)}</div>
                            <div class="stat-label">Modal Awal</div>
                        </div>
                        <div class="stat-card">
                            <div>📈</div>
                            <div class="stat-number positive">+{format_currency(total_tambahan_modal)}</div>
                            <div class="stat-label">Tambahan Modal</div>
                        </div>
                        <div class="stat-card">
                            <div>📉</div>
                            <div class="stat-number negative">-{format_currency(total_prive)}</div>
                            <div class="stat-label">Total Prive</div>
                        </div>
                        <div class="stat-card">
                            <div>🎯</div>
                            <div class="stat-number">{format_currency(modal_akhir)}</div>
                            <div class="stat-label">Modal Akhir</div>
                        </div>
                    </div>
                    
                    <!-- Perhitungan Modal -->
                    <div class="calculation-section">
                        <h3>🧮 Perhitungan Modal Akhir</h3>
                        <div class="calculation-step">
                            <span>Modal Awal</span>
                            <span>{format_currency(modal_awal)}</span>
                        </div>
                        <div class="calculation-step">
                            <span>Tambahan Modal</span>
                            <span class="positive">+ {format_currency(total_tambahan_modal)}</span>
                        </div>
                        <div class="calculation-step">
                            <span>Prive</span>
                            <span class="negative">- {format_currency(total_prive)}</span>
                        </div>
                        <div class="calculation-step">
                            <span>Laba/Rugi Bersih</span>
                            <span class="{ 'positive' if laba_bersih >= 0 else 'negative' }">{format_currency(laba_bersih)}</span>
                        </div>
                        <div class="calculation-step">
                            <span><strong>MODAL AKHIR</strong></span>
                            <span><strong>{format_currency(modal_akhir)}</strong></span>
                        </div>
                    </div>
                </div>
                
                <!-- Input Prive Section -->
                <div class="section">
                    <h2 class="section-title">📥 Input Pengambilan Prive</h2>
                    
                    <!-- Panduan Akun -->
                    <div class="akun-info">
                        <strong>📋 Jurnal Otomatis untuk Prive:</strong>
                        <br>• <strong>Debit:</strong> Prive (3120) - Pengurangan modal
                        <br>• <strong>Kredit:</strong> Kas/Bank - Pengurangan kas
                        <br>• <strong>Integrasi:</strong> Prive otomatis masuk ke Laporan Perubahan Modal
                    </div>
                    
                    <form method="POST">
                        <div class="form-grid">
                            <div class="form-group">
                                <label for="tanggal">📅 Tanggal Pengambilan:</label>
                                <input type="date" id="tanggal" name="tanggal" 
                                       value="{datetime.now().strftime('%Y-%m-%d')}" required>
                            </div>
                            <div class="form-group">
                                <label for="jumlah">💰 Jumlah Prive (Rp):</label>
                                <input type="number" id="jumlah" name="jumlah" 
                                       placeholder="0" step="1" min="1" required>
                            </div>
                            <div class="form-group">
                                <label for="metode_pembayaran">💳 Metode Pembayaran:</label>
                                <select id="metode_pembayaran" name="metode_pembayaran" required>
                                    <option value="CASH">💰 Cash</option>
                                    <option value="BANK">🏦 Transfer Bank</option>
                                </select>
                            </div>
                            <div class="form-group" style="grid-column: span 2;">
                                <label for="keterangan">📝 Keterangan Pengambilan:</label>
                                <input type="text" id="keterangan" name="keterangan" 
                                       placeholder="Contoh: Pengambilan untuk kebutuhan pribadi" required>
                            </div>
                        </div>
                        <button type="submit" name="add_prive" class="btn">💸 Catat Pengambilan Prive</button>
                    </form>
                </div>
                
                <!-- Input Tambahan Modal Section -->
                <div class="section">
                    <h2 class="section-title">📥 Input Tambahan Modal</h2>
                    
                    <!-- Panduan Akun -->
                    <div class="akun-info">
                        <strong>📋 Jurnal Otomatis untuk Tambahan Modal:</strong>
                        <br>• <strong>Debit:</strong> Kas/Bank - Penambahan kas
                        <br>• <strong>Kredit:</strong> Modal Pemilik (3110) - Penambahan modal
                    </div>
                    
                    <form method="POST">
                        <div class="form-grid">
                            <div class="form-group">
                                <label for="tanggal_tambahan">📅 Tanggal Setoran:</label>
                                <input type="date" id="tanggal_tambahan" name="tanggal_tambahan" 
                                       value="{datetime.now().strftime('%Y-%m-%d')}" required>
                            </div>
                            <div class="form-group">
                                <label for="jumlah_tambahan">💰 Jumlah Tambahan Modal (Rp):</label>
                                <input type="number" id="jumlah_tambahan" name="jumlah_tambahan" 
                                       placeholder="0" step="1" min="1" required>
                            </div>
                            <div class="form-group">
                                <label for="sumber_modal">🏦 Sumber Modal:</label>
                                <select id="sumber_modal" name="sumber_modal" required>
                                    <option value="CASH">💰 Cash</option>
                                    <option value="BANK">🏦 Transfer Bank</option>
                                    <option value="INVESTOR">👥 Investor</option>
                                    <option value="LAINNYA">📦 Sumber Lainnya</option>
                                </select>
                            </div>
                            <div class="form-group" style="grid-column: span 2;">
                                <label for="keterangan_tambahan">📝 Keterangan Tambahan Modal:</label>
                                <input type="text" id="keterangan_tambahan" name="keterangan_tambahan" 
                                       placeholder="Contoh: Setoran modal tambahan dari pemilik" required>
                            </div>
                        </div>
                        <button type="submit" name="add_tambahan_modal" class="btn">💰 Catat Tambahan Modal</button>
                    </form>
                </div>
                
                <!-- Daftar Prive -->
                <div class="section">
                    <h2 class="section-title">📋 Riwayat Pengambilan Prive</h2>
                    <div class="table-container">
                        <table>
                            <thead>
                                <tr>
                                    <th>📅 Tanggal</th>
                                    <th>👤 User</th>
                                    <th>💰 Jumlah</th>
                                    <th>💳 Metode</th>
                                    <th>📝 Keterangan</th>
                                    <th>📊 Jurnal</th>
                                </tr>
                            </thead>
                            <tbody>
                                {prive_rows if prive_data else '''
                                <tr>
                                    <td colspan="6" style="text-align: center; padding: 40px; color: #ff85b3;">
                                        💝 Belum ada pengambilan prive
                                    </td>
                                </tr>
                                '''}
                            </tbody>
                        </table>
                    </div>
                </div>
                
                <!-- Daftar Modal -->
                <div class="section">
                    <h2 class="section-title">📋 Riwayat Perubahan Modal</h2>
                    <div class="table-container">
                        <table>
                            <thead>
                                <tr>
                                    <th>📅 Tanggal</th>
                                    <th>👤 User</th>
                                    <th>🏷️ Tipe</th>
                                    <th>💰 Jumlah</th>
                                    <th>📝 Keterangan</th>
                                    <th>📊 Jurnal</th>
                                </tr>
                            </thead>
                            <tbody>
                                {modal_rows if modal_data else '''
                                <tr>
                                    <td colspan="6" style="text-align: center; padding: 40px; color: #ff85b3;">
                                        💝 Belum ada perubahan modal
                                    </td>
                                </tr>
                                '''}
                            </tbody>
                        </table>
                    </div>
                </div>
                
                <!-- Action Buttons -->
                <div class="section" style="text-align: center;">
                    <h2 class="section-title">⚡ Aksi Cepat</h2>
                    <div style="display: flex; gap: 15px; justify-content: center; flex-wrap: wrap;">
                        <a href="/jurnal-umum" class="btn btn-secondary">📝 Lihat Jurnal</a>
                        <a href="/neraca" class="btn btn-secondary">🏦 Lihat Neraca</a>
                        <a href="/laporan-perubahan-modal" class="btn btn-secondary">📊 Laporan Modal</a>
                        <button onclick="window.print()" class="btn">🖨️ Cetak Laporan</button>
                    </div>
                </div>
            </div>
        </div>
        
    </body>
    </html>
    """
    return prive_html

def generate_prive_rows(prive_data):
    """Generate HTML rows untuk data prive"""
    if not prive_data:
        return ""
    
    rows = []
    for prive in prive_data:
        row = f"""
        <tr>
            <td>{datetime.strptime(prive['tanggal'], '%Y-%m-%d').strftime('%d/%m/%Y')}</td>
            <td>
                <span class="user-badge {'current-user' if prive.get('user_email') == session.get('user_email') else ''}">
                    {prive.get('user_email', 'Unknown').split('@')[0]}
                </span>
            </td>
            <td><strong style="color: #ff6666;">-{format_currency(prive['jumlah'])}</strong></td>
            <td>
                <span style="padding: 4px 8px; border-radius: 8px; background: #66b3ff; color: white; font-size: 11px;">
                    {'💰 CASH' if prive.get('metode_pembayaran') == 'CASH' else '🏦 BANK'}
                </span>
            </td>
            <td>{prive.get('keterangan', '')}</td>
            <td>
                <small style="color: #666;">
                    💚 Prive (D) | ❤️ { 'Kas' if prive.get('metode_pembayaran') == 'CASH' else 'Bank' } (K)
                </small>
            </td>
        </tr>
        """
        rows.append(row)
    
    return "".join(rows)

def generate_modal_rows(modal_data):
    """Generate HTML rows untuk data modal"""
    if not modal_data:
        return ""
    
    rows = []
    for modal in modal_data:
        tipe = modal.get('tipe', '')
        is_positive = tipe in ['MODAL_AWAL', 'TAMBAHAN_MODAL']
        
        row = f"""
        <tr>
            <td>{datetime.strptime(modal['tanggal'], '%Y-%m-%d').strftime('%d/%m/%Y')}</td>
            <td>
                <span class="user-badge {'current-user' if modal.get('user_email') == session.get('user_email') else ''}">
                    {modal.get('user_email', 'Unknown').split('@')[0]}
                </span>
            </td>
            <td>
                <span style="padding: 4px 8px; border-radius: 8px; font-size: 11px; font-weight: bold; color: white; 
                      background: {'#00cc66' if tipe == 'MODAL_AWAL' else '#66b3ff' if tipe == 'TAMBAHAN_MODAL' else '#ff6666'}">
                    {tipe.replace('_', ' ')}
                </span>
            </td>
            <td>
                <strong style="color: {'#00cc66' if is_positive else '#ff6666'}">
                    {'+' if is_positive else '-'}{format_currency(modal['jumlah'])}
                </strong>
            </td>
            <td>{modal.get('keterangan', '')}</td>
            <td>
                <small style="color: #666;">
                    {f'💚 Kas/Bank (D) | ❤️ Modal (K)' if is_positive else '💚 Prive (D) | ❤️ Kas/Bank (K)'}
                </small>
            </td>
        </tr>
        """
        rows.append(row)
    
    return "".join(rows)

# ============================================================
# 🔹 ROUTE: Aset (Menu Utama)
# ============================================================
@app.route("/aset")
def aset():
    if not session.get('logged_in'):
        return redirect('/login')
    
    user_email = session.get('user_email')
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Manajemen Aset - PINKILANG</title>
        <meta charset="utf-8">
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: 'Arial', sans-serif;
                background: linear-gradient(135deg, #ffe6f2, #fff0f7);
                padding: 20px;
                min-height: 100vh;
            }}
            
            .container {{
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                border-radius: 15px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                overflow: hidden;
            }}
            
            .header {{
                background: linear-gradient(135deg, #ff85b3, #ff66a3);
                color: white;
                padding: 25px;
                text-align: center;
            }}
            
            .back-btn {{
                display: inline-block;
                padding: 10px 20px;
                background: rgba(255,255,255,0.2);
                color: white;
                text-decoration: none;
                border-radius: 8px;
                margin-bottom: 15px;
                border: 1px solid rgba(255,255,255,0.3);
            }}
            
            .back-btn:hover {{
                background: rgba(255,255,255,0.3);
            }}
            
            h1 {{
                font-size: 28px;
                margin-bottom: 10px;
            }}
            
            .content {{
                padding: 30px;
            }}
            
            .menu-grid {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 25px;
                margin-top: 20px;
            }}
            
            .menu-card {{
                background: #fff5f9;
                padding: 30px;
                border-radius: 12px;
                text-align: center;
                text-decoration: none;
                color: #333;
                transition: all 0.3s ease;
                border: 2px solid #ffd1e6;
                box-shadow: 0 4px 15px rgba(255,133,179,0.1);
            }}
            
            .menu-card:hover {{
                transform: translateY(-5px);
                box-shadow: 0 8px 25px rgba(255,133,179,0.2);
                border-color: #ff85b3;
                background: white;
            }}
            
            .menu-icon {{
                font-size: 48px;
                margin-bottom: 15px;
            }}
            
            .menu-title {{
                font-size: 20px;
                font-weight: bold;
                color: #ff66a3;
                margin-bottom: 10px;
            }}
            
            .menu-description {{
                color: #666;
                font-size: 14px;
                line-height: 1.5;
            }}
            
            .info-box {{
                background: #e6f7ff;
                border: 1px solid #91d5ff;
                border-radius: 10px;
                padding: 20px;
                margin: 20px 0;
                color: #0066cc;
            }}
            
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin: 25px 0;
            }}
            
            .stat-card {{
                background: white;
                padding: 20px;
                border-radius: 10px;
                text-align: center;
                box-shadow: 0 4px 15px rgba(255,133,179,0.1);
                border: 1px solid #ffe6f2;
            }}
            
            .stat-number {{
                font-size: 24px;
                font-weight: bold;
                color: #ff66a3;
                margin: 10px 0;
            }}
            
            .stat-label {{
                color: #e83e8c;
                font-size: 14px;
                font-weight: bold;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <!-- Header -->
            <div class="header">
                <a href="/dashboard" class="back-btn">← Kembali ke Dashboard</a>
                <h1>🏦 Manajemen Aset</h1>
                <p>Sistem Pencatatan Aset Lancar dan Tetap - PINKILANG</p>
            </div>
            
            <!-- Content -->
            <div class="content">
                <!-- Quick Stats -->
                <div class="stats-grid">
                    <div class="stat-card">
                        <div>💰</div>
                        <div class="stat-number" id="total-aset-lancar">Loading...</div>
                        <div class="stat-label">Total Aset Lancar</div>
                    </div>
                    <div class="stat-card">
                        <div>🏢</div>
                        <div class="stat-number" id="total-aset-tetap">Loading...</div>
                        <div class="stat-label">Total Aset Tetap</div>
                    </div>
                    <div class="stat-card">
                        <div>📊</div>
                        <div class="stat-number" id="total-semua-aset">Loading...</div>
                        <div class="stat-label">Total Semua Aset</div>
                    </div>
                </div>
                
                <!-- Menu Grid -->
                <div class="menu-grid">
                    <a href="/aset-lancar" class="menu-card">
                        <div class="menu-icon">💰</div>
                        <div class="menu-title">Aset Lancar</div>
                        <div class="menu-description">
                            Kelola aset lancar seperti kas, piutang, persediaan, dan perlengkapan.
                            Termasuk monitoring nilai perlengkapan dari transaksi operasional.
                        </div>
                    </a>
                    
                    <a href="/aset-tetap" class="menu-card">
                        <div class="menu-icon">🏢</div>
                        <div class="menu-title">Aset Tetap</div>
                        <div class="menu-description">
                            Kelola aset tetap seperti tanah, bangunan, kendaraan, dan peralatan.
                            Input nilai aset dan hitung penyusutan otomatis.
                        </div>
                    </a>
                </div>
                
                <!-- Additional Info -->
                <div style="text-align: center; margin-top: 30px; padding: 20px; background: #fff5f9; border-radius: 10px;">
                    <h3 style="color: #ff66a3; margin-bottom: 15px;">📋 Klasifikasi Aset</h3>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; text-align: left;">
                        <div>
                            <strong>Aset Lancar:</strong>
                            <ul style="margin-top: 10px; color: #666;">
                                <li>Kas & Bank</li>
                                <li>Piutang Usaha</li>
                                <li>Persediaan Barang</li>
                                <li>Perlengkapan</li>
                                <li>Beban Dibayar Dimuka</li>
                            </ul>
                        </div>
                        <div>
                            <strong>Aset Tetap:</strong>
                            <ul style="margin-top: 10px; color: #666;">
                                <li>Tanah</li>
                                <li>Bangunan</li>
                                <li>Kendaraan</li>
                                <li>Peralatan</li>
                                <li>Inventaris</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <script>
            // Load stats asynchronously
            async function loadAssetStats() {{
                try {{
                    // Simulate API call - in real implementation, you'd fetch from your backend
                    setTimeout(() => {{
                        document.getElementById('total-aset-lancar').textContent = 'Rp 25.000.000';
                        document.getElementById('total-aset-tetap').textContent = 'Rp 150.000.000';
                        document.getElementById('total-semua-aset').textContent = 'Rp 175.000.000';
                    }}, 500);
                }} catch (error) {{
                    console.error('Error loading stats:', error);
                }}
            }}
            
            // Load stats when page loads
            loadAssetStats();
        </script>
    </body>
    </html>
    """
    return html

def initialize_saldo_awal():
    """Inisialisasi saldo awal otomatis jika belum ada data"""
    try:
        # Cek apakah sudah ada saldo awal
        result = supabase.table("jurnal_umum")\
            .select("*")\
            .eq("transaksi_type", "SALDO_AWAL")\
            .execute()
        
        if not result.data:
            # Buat saldo awal default
            saldo_awal_entries = [
                {
                    "tanggal": "2024-01-01",
                    "nama_akun": "Kas",
                    "ref": "1110",
                    "debit": 10000000,  # Rp 10.000.000
                    "kredit": 0,
                    "deskripsi": "Saldo awal kas",
                    "transaksi_type": "SALDO_AWAL",
                    "user_email": "system",
                    "created_at": datetime.now().isoformat()
                },
                {
                    "tanggal": "2024-01-01", 
                    "nama_akun": "Kas di Bank",
                    "ref": "1120",
                    "debit": 5000000,  # Rp 5.000.000
                    "kredit": 0,
                    "deskripsi": "Saldo awal bank",
                    "transaksi_type": "SALDO_AWAL", 
                    "user_email": "system",
                    "created_at": datetime.now().isoformat()
                }
            ]
            
            for entry in saldo_awal_entries:
                supabase.table("jurnal_umum").insert(entry).execute()
            
            logger.info("✅ Saldo awal berhasil diinisialisasi")
            return True
            
        return True  # Sudah ada saldo awal
        
    except Exception as e:
        logger.error(f"❌ Error inisialisasi saldo awal: {str(e)}")
        return False

# ============================================================
# 🔹 ROUTE: Aset Lancar - FIXED VERSION (KAS SAJA)
# ============================================================
@app.route("/aset-lancar")
def aset_lancar():
    if not session.get('logged_in'):
        return redirect('/login')
    
    user_email = session.get('user_email')
    
    try:
        # 🔧 INISIALISASI SALDO AWAL JIKA PERLU
        initialize_saldo_awal()
        
        # 🔧 HITUNG SALDO DENGAN FUNGSI YANG SUDAH DIPERBAIKI
        saldo_data = hitung_saldo_aset_lancar_fixed()
        
        # Ambil data perlengkapan untuk tabel
        operasional_data = supabase.table("operasional")\
            .select("*")\
            .eq("jenis_pengeluaran", "PERLENGKAPAN")\
            .order("tanggal", desc=True)\
            .execute()
        
        perlengkapan_data = operasional_data.data or []
        
    except Exception as e:
        logger.error(f"Error di aset lancar: {str(e)}")
        saldo_data = {
            'kas': 0, 
            'piutang': 0,
            'persediaan': 0,
            'perlengkapan': 0,
            'total_aset_lancar': 0,
            'debug_info': {'error': str(e)}
        }
        perlengkapan_data = []
    
    # 🔧 FIX: Gunakan get() untuk akses yang aman
    kas_saldo = saldo_data.get('kas', 0)
    piutang_saldo = saldo_data.get('piutang', 0)
    persediaan_saldo = saldo_data.get('persediaan', 0)
    perlengkapan_saldo = saldo_data.get('perlengkapan', 0)
    total_aset = saldo_data.get('total_aset_lancar', 0)
    
    # 🔧 TAMPILKAN FORM SET SALDO JIKA MASIH 0
    kas_form = ""
    if kas_saldo <= 0:
        kas_form = f"""
        <!-- Form Set Saldo Manual -->
        <div class="section" style="background: #fff0f0; border-left: 5px solid #ff6666;">
            <h2 class="section-title">⚠️ Perhatian: Saldo Kas Masih Kosong</h2>
            <div class="info-box" style="background: #ffd4d4; color: #cc0000;">
                <strong>❌ Masalah Terdeteksi:</strong> Saldo Kas saat ini: <strong>{format_currency(kas_saldo)}</strong>
                <br>Hal ini bisa terjadi karena:
                <br>• Belum ada transaksi saldo awal
                <br>• Transaksi belum tercatat di jurnal
                <br>• Data jurnal tidak lengkap
            </div>
            
            <form method="POST" action="/set-saldo-awal-otomatis">
                <div style="text-align: center; padding: 20px;">
                    <button type="submit" class="btn" style="background: #ff6666; font-size: 18px; padding: 15px 30px;">
                        🔄 BUAT SALDO AWAL OTOMATIS
                    </button>
                    <p style="margin-top: 10px; color: #666; font-size: 14px;">
                        Sistem akan membuat saldo awal Kas: Rp 10.000.000
                    </p>
                </div>
            </form>
            
            <div style="margin-top: 20px; padding: 15px; background: #e6f7ff; border-radius: 8px;">
                <strong>💡 Atau atur manual:</strong>
                <form method="POST" action="/set-saldo-kas" style="margin-top: 10px;">
                    <div>
                        <label for="saldo_kas">💰 Set Saldo Kas Awal:</label>
                        <input type="number" name="saldo_kas" value="10000000" style="width: 100%; padding: 8px; font-size: 16px;">
                    </div>
                    <button type="submit" class="btn" style="background: #66b3ff; margin-top: 10px; font-size: 16px;">
                        💾 Simpan Saldo Kas
                    </button>
                </form>
            </div>
        </div>
        """
    
    # Generate table rows untuk perlengkapan
    perlengkapan_rows = ""
    if perlengkapan_data:
        for item in perlengkapan_data:
            try:
                tanggal = datetime.strptime(item.get('tanggal', ''), '%Y-%m-%d').strftime('%d/%m/%Y')
            except:
                tanggal = '-'
            
            perlengkapan_rows += f"""
                <tr>
                    <td>{tanggal}</td>
                    <td>{item.get('nama_barang', '-')}</td>
                    <td>{item.get('supplier', '-')}</td>
                    <td>{item.get('jumlah', 0)} {item.get('satuan', 'unit')}</td>
                    <td>{format_currency(item.get('harga_satuan', 0))}</td>
                    <td><strong>{format_currency(item.get('total_pengeluaran', 0))}</strong></td>
                    <td>
                        <span style="background: #ffb6d9; color: #c2185b; padding: 4px 8px; border-radius: 12px; font-size: 11px;">
                            {item.get('user_email', 'Unknown').split('@')[0]}
                        </span>
                    </td>
                </tr>
            """
    else:
        perlengkapan_rows = """
                <tr>
                    <td colspan="7" style="text-align: center; padding: 40px; color: #999;">
                        📊 Belum ada data perlengkapan
                        <br><br>
                        <a href="/operasional" style="color: #66b3ff; text-decoration: none;">
                            ➕ Input Transaksi Perlengkapan
                        </a>
                    </td>
                </tr>
        """
    
    # Data untuk chart persentase
    chart_data = []
    if total_aset > 0:
        chart_data = [
            {'name': 'Kas', 'value': kas_saldo, 'percentage': (kas_saldo / total_aset * 100) if total_aset > 0 else 0},
            {'name': 'Piutang', 'value': piutang_saldo, 'percentage': (piutang_saldo / total_aset * 100) if total_aset > 0 else 0},
            {'name': 'Persediaan', 'value': persediaan_saldo, 'percentage': (persediaan_saldo / total_aset * 100) if total_aset > 0 else 0},
            {'name': 'Perlengkapan', 'value': perlengkapan_saldo, 'percentage': (perlengkapan_saldo / total_aset * 100) if total_aset > 0 else 0}
        ]
    else:
        chart_data = [
            {'name': 'Kas', 'value': 0, 'percentage': 0},
            {'name': 'Piutang', 'value': 0, 'percentage': 0},
            {'name': 'Persediaan', 'value': 0, 'percentage': 0},
            {'name': 'Perlengkapan', 'value': 0, 'percentage': 0}
        ]
    
    chart_html = ""
    for item in chart_data:
        chart_html += f"""
            <div style="margin: 15px 0;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                    <span>{item['name']}</span>
                    <span>{item['percentage']:.1f}%</span>
                </div>
                <div style="background: #e6f2ff; border-radius: 10px; height: 10px;">
                    <div style="background: #66b3ff; height: 100%; border-radius: 10px; width: {item['percentage']}%;"></div>
                </div>
            </div>
        """
    
    # 🔧 DEBUG INFO
    debug_info = f"""
    <div class="section" style="background: #f8f9fa; border-left: 5px solid #999;">
        <h2 class="section-title">🔧 Debug Information</h2>
        <div style="font-family: monospace; font-size: 12px; background: white; padding: 15px; border-radius: 8px;">
            <strong>Data Perhitungan:</strong><br>
            • Kas: {format_currency(kas_saldo)}<br>
            • Piutang: {format_currency(piutang_saldo)}<br>
            • Persediaan: {format_currency(persediaan_saldo)}<br>
            • Perlengkapan: {format_currency(perlengkapan_saldo)}<br>
            • Total: {format_currency(total_aset)}<br>
            <br>
            <strong>Detail Debug:</strong><br>
            {json.dumps(saldo_data.get('debug_info', {}), indent=2)}
        </div>
                
        <!-- Quick Fix Button -->
        <div style="background: #fff0f0; border: 2px solid #ff6666; border-radius: 10px; padding: 20px; margin: 20px 0; text-align: center;">
            <h3 style="color: #ff6666; margin-bottom: 15px;">⚠️ Perhatian: Saldo Kas Tidak Normal</h3>
            <p style="color: #cc0000; margin-bottom: 15px;">
                Terdeteksi saldo Kas: <strong>{format_currency(kas_saldo)}</strong>
            </p>
            <a href="/fix-kas-data-complete" class="btn" style="background: #ff6666; color: white; padding: 12px 25px; text-decoration: none; border-radius: 8px; font-size: 16px;">
                🔧 PERBAIKI DATA KAS
            </a>
            <p style="color: #666; font-size: 12px; margin-top: 10px;">
                Klik tombol di atas untuk memperbaiki data Kas secara otomatis
            </p>
        </div>
    </div>
    """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Aset Lancar - PINKILANG</title>
        <meta charset="utf-8">
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: 'Arial', sans-serif;
                background: linear-gradient(135deg, #ffe6f2, #fff0f7);
                padding: 20px;
                min-height: 100vh;
            }}
            
            .container {{
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                border-radius: 15px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                overflow: hidden;
            }}
            
            .header {{
                background: linear-gradient(135deg, #66b3ff, #4d94ff);
                color: white;
                padding: 25px;
                text-align: center;
            }}
            
            .back-btn {{
                display: inline-block;
                padding: 10px 20px;
                background: rgba(255,255,255,0.2);
                color: white;
                text-decoration: none;
                border-radius: 8px;
                margin-bottom: 15px;
                border: 1px solid rgba(255,255,255,0.3);
            }}
            
            .back-btn:hover {{
                background: rgba(255,255,255,0.3);
            }}
            
            h1 {{
                font-size: 28px;
                margin-bottom: 10px;
            }}
            
            .content {{
                padding: 25px;
            }}
            
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin: 25px 0;
            }}
            
            .stat-card {{
                background: white;
                padding: 25px;
                border-radius: 12px;
                text-align: center;
                box-shadow: 0 4px 15px rgba(102,179,255,0.1);
                border: 2px solid #e6f2ff;
                transition: transform 0.3s ease;
            }}
            
            .stat-card:hover {{
                transform: translateY(-5px);
            }}
            
            .stat-icon {{
                font-size: 36px;
                margin-bottom: 15px;
            }}
            
            .stat-number {{
                font-size: 24px;
                font-weight: bold;
                color: #66b3ff;
                margin: 10px 0;
            }}
            
            .stat-number.negative {{
                color: #ff6666;
            }}
            
            .stat-label {{
                color: #3399ff;
                font-size: 14px;
                font-weight: bold;
            }}
            
            .section {{
                margin: 30px 0;
                padding: 25px;
                background: #f8fbff;
                border-radius: 12px;
                border-left: 5px solid #66b3ff;
            }}
            
            .section-title {{
                color: #66b3ff;
                font-size: 22px;
                margin-bottom: 20px;
                padding-bottom: 10px;
                border-bottom: 2px solid #e6f2ff;
            }}
            
            .table-container {{
                overflow-x: auto;
                margin-top: 15px;
            }}
            
            table {{
                width: 100%;
                border-collapse: collapse;
                background: white;
                border-radius: 8px;
                overflow: hidden;
                box-shadow: 0 4px 15px rgba(102,179,255,0.1);
            }}
            
            th, td {{
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid #e6f2ff;
            }}
            
            th {{
                background: #66b3ff;
                color: white;
                font-weight: bold;
            }}
            
            tr:hover {{
                background: #f0f8ff;
            }}
            
            .total-row {{
                background: #e6f2ff;
                font-weight: bold;
            }}
            
            .info-box {{
                background: #e6f7ff;
                border: 1px solid #91d5ff;
                border-radius: 8px;
                padding: 15px;
                margin: 15px 0;
                color: #0066cc;
            }}
            
            .form-group {{
                margin-bottom: 15px;
            }}
            
            label {{
                display: block;
                margin-bottom: 5px;
                color: #3399ff;
                font-weight: bold;
            }}
            
            input, textarea {{
                width: 100%;
                padding: 10px;
                border: 2px solid #b3d9ff;
                border-radius: 8px;
                font-size: 14px;
            }}
            
            .btn {{
                padding: 12px 25px;
                background: #66b3ff;
                color: white;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                font-size: 16px;
                text-decoration: none;
                display: inline-block;
                margin: 5px;
            }}
            
            .btn:hover {{
                background: #4d94ff;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <!-- Header -->
            <div class="header">
                <a href="/aset" class="back-btn">← Kembali ke Aset</a>
                <h1>💰 Aset Lancar</h1>
                <p>Manajemen Kas, Piutang, Persediaan, dan Perlengkapan</p>
            </div>
            
            <!-- Content -->
            <div class="content">
                <!-- Form Set Saldo Kas (Hanya muncul jika saldo 0) -->
                {kas_form}
                
                <!-- Summary Stats -->
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-icon">💵</div>
                        <div class="stat-number {'negative' if kas_saldo < 0 else ''}">
                            {format_currency(abs(kas_saldo))}
                            {'⚠️' if kas_saldo < 0 else ''}
                        </div>
                        <div class="stat-label">Kas</div>
                    </div>
                    
                    <div class="stat-card">
                        <div class="stat-icon">📄</div>
                        <div class="stat-number">{format_currency(piutang_saldo)}</div>
                        <div class="stat-label">Piutang Usaha</div>
                    </div>
                    
                    <div class="stat-card">
                        <div class="stat-icon">📦</div>
                        <div class="stat-number">{format_currency(persediaan_saldo)}</div>
                        <div class="stat-label">Persediaan Barang</div>
                    </div>
                    
                    <div class="stat-card">
                        <div class="stat-icon">🛠️</div>
                        <div class="stat-number">{format_currency(perlengkapan_saldo)}</div>
                        <div class="stat-label">Perlengkapan</div>
                    </div>
                </div>
                
                <!-- Total Aset Lancar -->
                <div style="text-align: center; margin: 30px 0; padding: 20px; background: linear-gradient(135deg, #66b3ff, #4d94ff); color: white; border-radius: 10px;">
                    <h2 style="margin-bottom: 10px;">Total Aset Lancar</h2>
                    <div style="font-size: 32px; font-weight: bold;">
                        {format_currency(total_aset)}
                    </div>
                </div>
                
                <!-- Perlengkapan Section -->
                <div class="section">
                    <h2 class="section-title">🛠️ Data Perlengkapan</h2>
                    <p>Data diambil dari transaksi operasional dengan jenis pengeluaran "Perlengkapan"</p>
                    
                    <div class="table-container">
                        <table>
                            <thead>
                                <tr>
                                    <th>Tanggal</th>
                                    <th>Nama Barang</th>
                                    <th>Supplier</th>
                                    <th>Jumlah</th>
                                    <th>Harga Satuan</th>
                                    <th>Total</th>
                                    <th>Input Oleh</th>
                                </tr>
                            </thead>
                            <tbody>
                                {perlengkapan_rows}
                                {f'<tr class="total-row"><td colspan="5" style="text-align: right;"><strong>Total Nilai Perlengkapan:</strong></td><td colspan="2"><strong>{format_currency(perlengkapan_saldo)}</strong></td></tr>' if perlengkapan_data else ''}
                            </tbody>
                        </table>
                    </div>
                </div>
                
                <!-- Breakdown Aset Lancar -->
                <div class="section">
                    <h2 class="section-title">📊 Breakdown Aset Lancar</h2>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                        <div>
                            <h3 style="color: #66b3ff; margin-bottom: 15px;">Komposisi Aset Lancar</h3>
                            <div style="background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                                <div style="display: flex; justify-content: space-between; margin: 10px 0; padding: 8px; border-bottom: 1px solid #f0f0f0;">
                                    <span>Kas:</span>
                                    <strong>{format_currency(kas_saldo)}</strong>
                                </div>
                                <div style="display: flex; justify-content: space-between; margin: 10px 0; padding: 8px; border-bottom: 1px solid #f0f0f0;">
                                    <span>Piutang Usaha:</span>
                                    <strong>{format_currency(piutang_saldo)}</strong>
                                </div>
                                <div style="display: flex; justify-content: space-between; margin: 10px 0; padding: 8px; border-bottom: 1px solid #f0f0f0;">
                                    <span>Persediaan:</span>
                                    <strong>{format_currency(persediaan_saldo)}</strong>
                                </div>
                                <div style="display: flex; justify-content: space-between; margin: 10px 0; padding: 8px;">
                                    <span>Perlengkapan:</span>
                                    <strong>{format_currency(perlengkapan_saldo)}</strong>
                                </div>
                            </div>
                        </div>
                        
                        <div>
                            <h3 style="color: #66b3ff; margin-bottom: 15px;">Persentase</h3>
                            <div style="background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                                {chart_html}
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Debug Information -->
                {debug_info if kas_saldo <= 0 else ''}
                
                <!-- Action Buttons -->
                <div style="text-align: center; margin-top: 30px;">
                    <a href="/operasional" class="btn">
                        ➕ Input Perlengkapan
                    </a>
                    <a href="/penjualan" class="btn" style="background: #ff66a3;">
                        📊 Lihat Piutang
                    </a>
                    <a href="/jurnal-umum" class="btn" style="background: #00cc66;">
                        📝 Lihat Jurnal
                    </a>
                    <button onclick="window.print()" class="btn" style="background: #ff9966;">
                        🖨️ Cetak Laporan
                    </button>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return html

# ============================================================
# 🔹 FUNGSI BANTU YANG SUDAH DIPERBAIKI (KAS SAJA)
# ============================================================

def hitung_saldo_aset_lancar_fixed():
    """Hitung saldo aset lancar - FIXED VERSION (KAS SAJA)"""
    try:
        # 1. HITUNG KAS SAJA
        kas_data = supabase.table("jurnal_umum")\
            .select("nama_akun, debit, kredit")\
            .eq("nama_akun", "Kas")\
            .execute()
        
        kas_list = kas_data.data or []
        
        saldo_kas = 0
        
        for transaksi in kas_list:
            debit = float(transaksi.get('debit', 0) or 0)
            kredit = float(transaksi.get('kredit', 0) or 0)
            saldo_kas += (debit - kredit)

        # 2. HITUNG PIUTANG
        piutang_data = supabase.table("jurnal_umum")\
            .select("debit, kredit")\
            .eq("nama_akun", "Piutang Usaha")\
            .execute()
        
        piutang_list = piutang_data.data or []
        saldo_piutang = sum(float(item.get('debit', 0) or 0) for item in piutang_list) - \
                       sum(float(item.get('kredit', 0) or 0) for item in piutang_list)
        
        # 3. HITUNG PERSEDIAAN
        persediaan_data = supabase.table("persediaan_terintegrasi")\
            .select("*")\
            .eq("id", 1)\
            .execute()
        
        if persediaan_data.data:
            persediaan = persediaan_data.data[0]
            jumlah_persediaan = persediaan.get('jumlah_persediaan', 0)
            nilai_persediaan = jumlah_persediaan * 350  # Harga rata-rata
        else:
            nilai_persediaan = 0
            jumlah_persediaan = 0
        
        # 4. HITUNG PERLENGKAPAN
        operasional_data = supabase.table("operasional")\
            .select("total_pengeluaran")\
            .eq("jenis_pengeluaran", "PERLENGKAPAN")\
            .execute()
        
        perlengkapan_list = operasional_data.data or []
        total_perlengkapan = sum(float(item.get('total_pengeluaran', 0) or 0) for item in perlengkapan_list)
        
        # 🔧 FIX: Return dengan key 'kas' saja
        return {
            'kas': saldo_kas,  # Key utama yang digunakan di route
            'piutang': max(0, saldo_piutang),
            'persediaan': nilai_persediaan,
            'perlengkapan': total_perlengkapan,
            'total_aset_lancar': max(0, saldo_kas) + max(0, saldo_piutang) + nilai_persediaan + total_perlengkapan,
            'debug_info': {
                'kas': saldo_kas,
                'piutang_raw': saldo_piutang,
                'persediaan_unit': jumlah_persediaan,
                'total_transaksi_kas': len(kas_list),
                'total_transaksi_piutang': len(piutang_list)
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error hitung saldo aset lancar: {str(e)}")
        return {
            'kas': 0,
            'piutang': 0, 
            'persediaan': 0,
            'perlengkapan': 0,
            'total_aset_lancar': 0,
            'debug_info': {'error': str(e)}
        }

def initialize_saldo_awal():
    """Inisialisasi saldo awal otomatis jika belum ada data"""
    try:
        # Cek apakah sudah ada saldo awal
        result = supabase.table("jurnal_umum")\
            .select("*")\
            .eq("transaksi_type", "SALDO_AWAL")\
            .execute()
        
        if not result.data:
            # Buat saldo awal default
            saldo_awal_entry = {
                "tanggal": "2024-01-01",
                "nama_akun": "Kas",
                "ref": "1110",
                "debit": 10000000,
                "kredit": 0,
                "deskripsi": "Saldo awal kas",
                "transaksi_type": "SALDO_AWAL",
                "user_email": "system",
                "created_at": datetime.now().isoformat()
            }
            
            supabase.table("jurnal_umum").insert(saldo_awal_entry).execute()
            logger.info("✅ Saldo awal Kas berhasil diinisialisasi")
            return True
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Error inisialisasi saldo awal: {str(e)}")
        return False

# ============================================================
# 🔹 ROUTE UNTUK SET SALDO KAS - FIXED
# ============================================================

@app.route("/set-saldo-awal-otomatis", methods=["POST"])
def set_saldo_awal_otomatis():
    if not session.get('logged_in'):
        return redirect('/login')
    
    user_email = session.get('user_email')
    
    try:
        # Hapus saldo awal lama jika ada
        supabase.table("jurnal_umum")\
            .delete()\
            .eq("transaksi_type", "SALDO_AWAL")\
            .execute()
        
        # Buat saldo awal baru
        saldo_entry = {
            "tanggal": datetime.now().strftime('%Y-%m-%d'),
            "nama_akun": "Kas",
            "ref": "1110", 
            "debit": 10000000,
            "kredit": 0,
            "deskripsi": "Saldo awal kas - Generated by System",
            "transaksi_type": "SALDO_AWAL",
            "user_email": user_email,
            "created_at": datetime.now().isoformat()
        }
        
        result = supabase.table("jurnal_umum").insert(saldo_entry).execute()
        
        if result.data:
            session['flash_message'] = "✅ Saldo awal berhasil dibuat! Kas: Rp 10.000.000"
            logger.info(f"✅ Saldo awal otomatis berhasil dibuat oleh {user_email}")
        else:
            session['flash_message'] = "❌ Gagal membuat saldo awal"
            
    except Exception as e:
        logger.error(f"❌ Error set saldo awal otomatis: {str(e)}")
        session['flash_message'] = f"❌ Error: {str(e)}"
    
    return redirect("/aset-lancar")

@app.route("/set-saldo-kas", methods=["POST"])
def set_saldo_kas():
    if not session.get('logged_in'):
        return redirect('/login')
    
    user_email = session.get('user_email')
    
    try:
        saldo_kas = int(request.form.get("saldo_kas", 0) or 0)
        
        if saldo_kas <= 0:
            session['flash_message'] = "❌ Saldo harus lebih dari 0"
            return redirect("/aset-lancar")
        
        # Hapus saldo lama untuk akun Kas
        supabase.table("jurnal_umum")\
            .delete()\
            .eq("transaksi_type", "SALDO_AWAL")\
            .execute()
        
        jurnal_entry = {
            "tanggal": datetime.now().strftime('%Y-%m-%d'),
            "nama_akun": "Kas",
            "ref": "1110",
            "debit": saldo_kas,
            "kredit": 0,
            "deskripsi": "Saldo awal kas - Manual Entry",
            "transaksi_type": "SALDO_AWAL",
            "user_email": user_email,
            "created_at": datetime.now().isoformat()
        }
        
        result = supabase.table("jurnal_umum").insert(jurnal_entry).execute()
        
        if result.data:
            session['flash_message'] = f"✅ Saldo Kas berhasil diatur! Jumlah: {format_currency(saldo_kas)}"
        else:
            session['flash_message'] = "❌ Gagal mengatur saldo Kas"
            
    except Exception as e:
        logger.error(f"❌ Error set saldo kas: {str(e)}")
        session['flash_message'] = f"❌ Error: {str(e)}"
    
    return redirect("/aset-lancar")

@app.route("/fix-kas-data-complete")
def fix_kas_data_complete():
    if not session.get('logged_in'):
        return redirect('/login')
    
    user_email = session.get('user_email')
    
    try:
        # 1. Hapus semua transaksi Kas yang bermasalah
        supabase.table("jurnal_umum")\
            .delete()\
            .eq("nama_akun", "Kas")\
            .execute()
        
        # 2. Buat saldo awal yang benar
        saldo_entry = {
            "tanggal": datetime.now().strftime('%Y-%m-%d'),
            "nama_akun": "Kas",
            "ref": "1110", 
            "debit": 15000000,
            "kredit": 0,
            "deskripsi": "SALDO AWAL KAS - System Fixed",
            "transaksi_type": "SALDO_AWAL",
            "user_email": user_email,
            "created_at": datetime.now().isoformat()
        }
        
        result = supabase.table("jurnal_umum").insert(saldo_entry).execute()
        
        if result.data:
            session['flash_message'] = "✅ Data Kas berhasil diperbaiki! Saldo awal: Rp 15.000.000"
            logger.info(f"✅ Data Kas berhasil difixed oleh {user_email}")
        else:
            session['flash_message'] = "❌ Gagal memperbaiki data Kas"
        
    except Exception as e:
        logger.error(f"❌ Error fix kas data complete: {str(e)}")
        session['flash_message'] = f"❌ Error: {str(e)}"
    
    return redirect("/aset-lancar")

# ============================================================
# 🔹 FUNGSI BANTU FORMAT CURRENCY
# ============================================================

def format_currency(amount):
    """Format angka menjadi format currency Indonesia"""
    try:
        amount = float(amount or 0)
        return "Rp {:,.0f}".format(amount).replace(",", ".")
    except:
        return "Rp 0"
        
# ============================================================
# 🔹 ROUTE: Aset Tetap
# ============================================================
@app.route("/aset-tetap", methods=["GET", "POST"])
def aset_tetap():
    if not session.get('logged_in'):
        return redirect('/login')
    
    user_email = session.get('user_email')
    message = ""
    
    # Handle form submission
    if request.method == "POST":
        message = process_aset_tetap_form(user_email)
    
    # Ambil data aset tetap
    aset_tetap_data = get_aset_tetap_data()
    
    # Hitung totals
    total_nilai_aset = sum(item.get('nilai_perolehan', 0) for item in aset_tetap_data)
    total_penyusutan = sum(item.get('akumulasi_penyusutan', 0) for item in aset_tetap_data)
    total_nilai_buku = total_nilai_aset - total_penyusutan
    
    html = generate_aset_tetap_html(user_email, message, aset_tetap_data, total_nilai_aset, total_penyusutan, total_nilai_buku)
    return html

def process_aset_tetap_form(user_email):
    """Process form input aset tetap"""
    try:
        # Collect form data
        tanggal_perolehan = request.form.get("tanggal_perolehan")
        jenis_aset = request.form.get("jenis_aset")
        nama_aset = request.form.get("nama_aset")
        nilai_perolehan = int(request.form.get("nilai_perolehan", 0))
        masa_manfaat = int(request.form.get("masa_manfaat", 0))  # dalam tahun
        nilai_residu = int(request.form.get("nilai_residu", 0))
        keterangan = request.form.get("keterangan", "")
        
        if not all([tanggal_perolehan, jenis_aset, nama_aset]):
            return '<div class="message error">❌ Semua field wajib diisi!</div>'
        
        if nilai_perolehan <= 0:
            return '<div class="message error">❌ Nilai perolehan harus lebih dari 0!</div>'
        
        if masa_manfaat <= 0:
            return '<div class="message error">❌ Masa manfaat harus lebih dari 0!</div>'
        
        # Hitung penyusutan tahunan (metode garis lurus)
        penyusutan_tahunan = (nilai_perolehan - nilai_residu) / masa_manfaat
        
        # Simpan data aset tetap
        aset_data = {
            "user_email": user_email,
            "tanggal_perolehan": tanggal_perolehan,
            "jenis_aset": jenis_aset,
            "nama_aset": nama_aset,
            "nilai_perolehan": nilai_perolehan,
            "masa_manfaat": masa_manfaat,
            "nilai_residu": nilai_residu,
            "penyusutan_tahunan": penyusutan_tahunan,
            "akumulasi_penyusutan": 0,  # Awalnya 0
            "nilai_buku": nilai_perolehan,
            "keterangan": keterangan,
            "created_at": datetime.now().isoformat()
        }
        
        if supabase:
            # Insert ke tabel aset_tetap
            insert_result = supabase.table("aset_tetap").insert(aset_data).execute()
            
            if insert_result and insert_result.data:
                # Buat jurnal untuk pembelian aset tetap
                jurnal_entries = [
                    {
                        "tanggal": tanggal_perolehan,
                        "nama_akun": get_akun_aset_tetap(jenis_aset),
                        "ref": get_kode_akun_aset(jenis_aset),
                        "debit": nilai_perolehan,
                        "kredit": 0,
                        "deskripsi": f"Pembelian {jenis_aset.lower()}: {nama_aset}",
                        "transaksi_type": "PEMBELIAN_ASET",
                        "user_email": user_email,
                        "created_at": datetime.now().isoformat()
                    },
                    {
                        "tanggal": tanggal_perolehan,
                        "nama_akun": "Kas",
                        "ref": "1110",
                        "debit": 0,
                        "kredit": nilai_perolehan,
                        "deskripsi": f"Pembayaran {jenis_aset.lower()}: {nama_aset}",
                        "transaksi_type": "PEMBELIAN_ASET",
                        "user_email": user_email,
                        "created_at": datetime.now().isoformat()
                    }
                ]
                
                # Simpan jurnal
                success_count = 0
                for entry in jurnal_entries:
                    try:
                        result = supabase.table("jurnal_umum").insert(entry).execute()
                        if result.data:
                            success_count += 1
                    except Exception as e:
                        logger.error(f"Error insert jurnal aset tetap: {str(e)}")
                
                logger.info(f"✅ Aset tetap berhasil dicatat: {nama_aset} oleh {user_email}")
                return f'<div class="message success">✅ Aset tetap berhasil dicatat! Jurnal otomatis dibuat.</div>'
            else:
                return '<div class="message error">❌ Gagal menyimpan data aset tetap!</div>'
        else:
            return '<div class="message error">❌ Database connection error!</div>'
                
    except Exception as e:
        logger.error(f"❌ Error proses aset tetap: {str(e)}")
        return f'<div class="message error">❌ Error mencatat aset tetap: {str(e)}</div>'

def get_akun_aset_tetap(jenis_aset):
    """Get nama akun berdasarkan jenis aset"""
    akun_map = {
        "TANAH": "Tanah",
        "BANGUNAN": "Bangunan",
        "KENDARAAN": "Kendaraan",
        "PERALATAN": "Peralatan",
        "INVENTARIS": "Inventaris Kantor"
    }
    return akun_map.get(jenis_aset, "Aset Tetap")

def get_kode_akun_aset(jenis_aset):
    """Get kode akun berdasarkan jenis aset"""
    kode_map = {
        "TANAH": "1261",
        "BANGUNAN": "1262",
        "KENDARAAN": "1263",
        "PERALATAN": "1264",
        "INVENTARIS": "1265"
    }
    return kode_map.get(jenis_aset, "1200")

def get_aset_tetap_data():
    """Ambil data aset tetap dari database"""
    try:
        if supabase:
            result = supabase.table("aset_tetap").select("*").order("tanggal_perolehan", desc=True).execute()
            return result.data or []
        else:
            return []
    except Exception as e:
        logger.error(f"Error ambil data aset tetap: {str(e)}")
        return []

def generate_aset_tetap_html(user_email, message, aset_tetap_data, total_nilai_aset, total_penyusutan, total_nilai_buku):
    """Generate HTML untuk halaman aset tetap"""
    
    def format_currency(amount):
        return f"Rp {amount:,.0f}".replace(",", ".")
    
    # Generate form input
    input_form = f"""
    <div class="section">
        <h2 class="section-title">➕ Input Aset Tetap Baru</h2>
        
        <form method="POST">
            <div class="form-grid">
                <div class="form-group">
                    <label for="tanggal_perolehan">📅 Tanggal Perolehan:</label>
                    <input type="date" id="tanggal_perolehan" name="tanggal_perolehan" 
                           value="{datetime.now().strftime('%Y-%m-%d')}" required>
                </div>
                <div class="form-group">
                    <label for="jenis_aset">🏷️ Jenis Aset:</label>
                    <select id="jenis_aset" name="jenis_aset" required>
                        <option value="">Pilih Jenis Aset</option>
                        <option value="TANAH">Tanah</option>
                        <option value="BANGUNAN">Bangunan</option>
                        <option value="KENDARAAN">Kendaraan</option>
                        <option value="PERALATAN">Peralatan</option>
                        <option value="INVENTARIS">Inventaris</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="nama_aset">📝 Nama Aset:</label>
                    <input type="text" id="nama_aset" name="nama_aset" 
                           placeholder="Contoh: Toyota Avanza, Laptop Dell, dll" required>
                </div>
                <div class="form-group">
                    <label for="nilai_perolehan">💰 Nilai Perolehan (Rp):</label>
                    <input type="number" id="nilai_perolehan" name="nilai_perolehan" 
                           placeholder="0" step="1" min="1" required>
                </div>
                <div class="form-group">
                    <label for="masa_manfaat">⏰ Masa Manfaat (tahun):</label>
                    <input type="number" id="masa_manfaat" name="masa_manfaat" 
                           placeholder="0" step="1" min="1" required>
                </div>
                <div class="form-group">
                    <label for="nilai_residu">🎯 Nilai Residu (Rp):</label>
                    <input type="number" id="nilai_residu" name="nilai_residu" 
                           placeholder="0" step="1" min="0">
                </div>
                <div class="form-group">
                    <label for="metode_pembayaran">💳 Metode Pembayaran:</label>
                    <select id="metode_pembayaran" name="metode_pembayaran" required>
                        <option value="CASH">Cash</option>
                        <option value="BANK">Transfer Bank</option>
                    </select>
                </div>
                <div class="form-group" style="grid-column: span 2;">
                    <label for="keterangan">📋 Keterangan (Opsional):</label>
                    <textarea id="keterangan" name="keterangan" 
                              placeholder="Tambahkan keterangan tentang aset..." rows="3"></textarea>
                </div>
            </div>
            
            <div class="akun-info">
                <strong>📋 Jurnal Otomatis akan dibuat:</strong>
                <br>• <strong>Debit:</strong> Akun Aset Tetap (sesuai jenis)
                <br>• <strong>Kredit:</strong> Kas/Bank (pengurangan kas)
            </div>
            
            <button type="submit" class="btn">💾 Simpan Aset Tetap</button>
        </form>
    </div>
    """
    
    # Generate table rows
    table_rows = ""
    if aset_tetap_data:
        for aset in aset_tetap_data:
            # Hitung umur aset
            try:
                tanggal_perolehan = datetime.strptime(aset.get('tanggal_perolehan', ''), '%Y-%m-%d')
                umur_bulan = (datetime.now() - tanggal_perolehan).days // 30
            except:
                umur_bulan = 0
            
            table_rows += f"""
            <tr>
                <td>{tanggal_perolehan.strftime('%d/%m/%Y') if 'tanggal_perolehan' in aset else '-'}</td>
                <td>
                    <span style="padding: 4px 8px; border-radius: 12px; font-size: 11px; font-weight: bold; color: white; 
                          background: {get_jenis_aset_color(aset.get('jenis_aset', ''))}">
                        {aset.get('jenis_aset', '-')}
                    </span>
                </td>
                <td><strong>{aset.get('nama_aset', '-')}</strong></td>
                <td class="number">{format_currency(aset.get('nilai_perolehan', 0))}</td>
                <td class="number">{format_currency(aset.get('penyusutan_tahunan', 0))}/tahun</td>
                <td class="number">{format_currency(aset.get('akumulasi_penyusutan', 0))}</td>
                <td class="number"><strong>{format_currency(aset.get('nilai_buku', 0))}</strong></td>
                <td>{umur_bulan} bulan</td>
                <td>{aset.get('keterangan', '-')}</td>
            </tr>
            """
    else:
        table_rows = """
        <tr>
            <td colspan="9" style="text-align: center; padding: 40px; color: #999;">
                🏢 Belum ada data aset tetap
                <br><br>
                Gunakan form di atas untuk menambahkan aset tetap pertama Anda.
            </td>
        </tr>
        """
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Aset Tetap - PINKILANG</title>
        <meta charset="utf-8">
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: 'Arial', sans-serif;
                background: linear-gradient(135deg, #ffe6f2, #fff0f7);
                padding: 20px;
                min-height: 100vh;
            }}
            
            .container {{
                max-width: 1400px;
                margin: 0 auto;
                background: white;
                border-radius: 15px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                overflow: hidden;
            }}
            
            .header {{
                background: linear-gradient(135deg, #00cc66, #00b359);
                color: white;
                padding: 25px;
                text-align: center;
            }}
            
            .back-btn {{
                display: inline-block;
                padding: 10px 20px;
                background: rgba(255,255,255,0.2);
                color: white;
                text-decoration: none;
                border-radius: 8px;
                margin-bottom: 15px;
                border: 1px solid rgba(255,255,255,0.3);
            }}
            
            .back-btn:hover {{
                background: rgba(255,255,255,0.3);
            }}
            
            h1 {{
                font-size: 28px;
                margin-bottom: 10px;
            }}
            
            .content {{
                padding: 25px;
            }}
            
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin: 25px 0;
            }}
            
            .stat-card {{
                background: white;
                padding: 25px;
                border-radius: 12px;
                text-align: center;
                box-shadow: 0 4px 15px rgba(0,204,102,0.1);
                border: 2px solid #e6f7f0;
                transition: transform 0.3s ease;
            }}
            
            .stat-card:hover {{
                transform: translateY(-5px);
            }}
            
            .stat-icon {{
                font-size: 36px;
                margin-bottom: 15px;
            }}
            
            .stat-number {{
                font-size: 24px;
                font-weight: bold;
                color: #00cc66;
                margin: 10px 0;
            }}
            
            .stat-label {{
                color: #00994d;
                font-size: 14px;
                font-weight: bold;
            }}
            
            .section {{
                margin: 30px 0;
                padding: 25px;
                background: #f0faf5;
                border-radius: 12px;
                border-left: 5px solid #00cc66;
            }}
            
            .section-title {{
                color: #00cc66;
                font-size: 22px;
                margin-bottom: 20px;
                padding-bottom: 10px;
                border-bottom: 2px solid #e6f7f0;
            }}
            
            .form-grid {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
                margin-bottom: 20px;
            }}
            
            .form-group {{
                margin-bottom: 15px;
            }}
            
            label {{
                display: block;
                margin-bottom: 5px;
                color: #00994d;
                font-weight: bold;
            }}
            
            input, select, textarea {{
                width: 100%;
                padding: 12px;
                border: 2px solid #b3e6cc;
                border-radius: 8px;
                font-size: 16px;
                transition: border-color 0.3s ease;
                background: white;
            }}
            
            input:focus, select:focus, textarea:focus {{
                border-color: #00cc66;
                outline: none;
                box-shadow: 0 0 0 3px rgba(0,204,102,0.1);
            }}
            
            .btn {{
                padding: 12px 30px;
                background: linear-gradient(135deg, #00cc66, #00b359);
                color: white;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                font-size: 16px;
                transition: all 0.3s ease;
                font-weight: bold;
            }}
            
            .btn:hover {{
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(0,204,102,0.3);
            }}
            
            .table-container {{
                overflow-x: auto;
                margin-top: 15px;
            }}
            
            table {{
                width: 100%;
                border-collapse: collapse;
                background: white;
                border-radius: 8px;
                overflow: hidden;
                box-shadow: 0 4px 15px rgba(0,204,102,0.1);
            }}
            
            th, td {{
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid #e6f7f0;
            }}
            
            th {{
                background: #00cc66;
                color: white;
                font-weight: bold;
            }}
            
            tr:hover {{
                background: #f0faf5;
            }}
            
            .number {{
                text-align: right;
                font-family: 'Courier New', monospace;
            }}
            
            .total-row {{
                background: #e6f7f0;
                font-weight: bold;
            }}
            
            .info-box {{
                background: #e6f7ff;
                border: 1px solid #91d5ff;
                border-radius: 8px;
                padding: 15px;
                margin: 15px 0;
                color: #0066cc;
            }}
            
            .akun-info {{
                background: #e6f7f0;
                border: 1px solid #b3e6cc;
                border-radius: 8px;
                padding: 10px;
                margin: 10px 0;
                font-size: 12px;
                color: #00994d;
            }}
            
            .message {{
                padding: 15px;
                margin: 15px 0;
                border-radius: 8px;
                font-size: 14px;
            }}
            
            .success {{
                background: #d4edda;
                color: #155724;
                border: 1px solid #c3e6cb;
            }}
            
            .error {{
                background: #f8d7da;
                color: #721c24;
                border: 1px solid #f5c6cb;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <!-- Header -->
            <div class="header">
                <a href="/aset" class="back-btn">← Kembali ke Aset</a>
                <h1>🏢 Aset Tetap</h1>
                <p>Manajemen Tanah, Bangunan, Kendaraan, dan Peralatan</p>
            </div>
            
            <!-- Content -->
            <div class="content">
                {message}
                
                <!-- Summary Stats -->
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-icon">💰</div>
                        <div class="stat-number">{format_currency(total_nilai_aset)}</div>
                        <div class="stat-label">Nilai Perolehan</div>
                    </div>
                    
                    <div class="stat-card">
                        <div class="stat-icon">📉</div>
                        <div class="stat-number">{format_currency(total_penyusutan)}</div>
                        <div class="stat-label">Akumulasi Penyusutan</div>
                    </div>
                    
                    <div class="stat-card">
                        <div class="stat-icon">📊</div>
                        <div class="stat-number">{format_currency(total_nilai_buku)}</div>
                        <div class="stat-label">Nilai Buku</div>
                    </div>
                    
                    <div class="stat-card">
                        <div class="stat-icon">📋</div>
                        <div class="stat-number">{len(aset_tetap_data)}</div>
                        <div class="stat-label">Jumlah Aset</div>
                    </div>
                </div>
                
                <!-- Input Form -->
                {input_form}
                
                <!-- Daftar Aset Tetap -->
                <div class="section">
                    <h2 class="section-title">📋 Daftar Aset Tetap</h2>
                    
                    <div class="table-container">
                        <table>
                            <thead>
                                <tr>
                                    <th>Tanggal</th>
                                    <th>Jenis</th>
                                    <th>Nama Aset</th>
                                    <th>Nilai Perolehan</th>
                                    <th>Penyusutan/Tahun</th>
                                    <th>Akumulasi Penyusutan</th>
                                    <th>Nilai Buku</th>
                                    <th>Umur</th>
                                    <th>Keterangan</th>
                                </tr>
                            </thead>
                            <tbody>
                                {table_rows}
                                {f'<tr class="total-row"><td colspan="3"><strong>TOTAL</strong></td><td class="number"><strong>{format_currency(total_nilai_aset)}</strong></td><td class="number">-</td><td class="number"><strong>{format_currency(total_penyusutan)}</strong></td><td class="number"><strong>{format_currency(total_nilai_buku)}</strong></td><td colspan="2">-</td></tr>' if aset_tetap_data else ''}
                            </tbody>
                        </table>
                    </div>
                </div>
                
                <!-- Action Buttons -->
                <div style="text-align: center; margin-top: 30px;">
                    <a href="/jurnal-umum" style="display: inline-block; padding: 12px 25px; background: #00cc66; color: white; text-decoration: none; border-radius: 8px; margin: 0 10px;">
                        📝 Lihat Jurnal
                    </a>
                    <a href="/neraca" style="display: inline-block; padding: 12px 25px; background: #ff66a3; color: white; text-decoration: none; border-radius: 8px; margin: 0 10px;">
                        🏦 Lihat Neraca
                    </a>
                    <button onclick="window.print()" style="padding: 12px 25px; background: #66b3ff; color: white; border: none; border-radius: 8px; margin: 0 10px; cursor: pointer;">
                        🖨️ Cetak Laporan
                    </button>
                </div>
            </div>
        </div>
        
    </body>
    </html>
    """
    return html

def get_jenis_aset_color(jenis_aset):
    """Get color for asset type badge"""
    color_map = {
        "TANAH": "#8B4513",
        "BANGUNAN": "#FF6B6B", 
        "KENDARAAN": "#4ECDC4",
        "PERALATAN": "#45B7D1",
        "INVENTARIS": "#96CEB4"
    }
    return color_map.get(jenis_aset, "#666666")

# ============================================================
# 🔹 ROUTE: Hapus Transaksi Massal (Multi-Select) - DIPERBAIKI
# ============================================================
@app.route("/hapus-transaksi-massal", methods=["GET", "POST"])
def hapus_transaksi_massal():
    if not session.get('logged_in'):
        return redirect('/login')
    
    user_email = session.get('user_email')
    message = ""
    
    # Handle POST request untuk hapus massal
    if request.method == "POST":
        selected_transactions = request.form.getlist("selected_transactions")
        action = request.form.get("action")
        konfirmasi = request.form.get("konfirmasi")
        
        if action == "delete_selected" and selected_transactions:
            if konfirmasi != "YA":
                message = '<div class="message error">❌ Konfirmasi penghapusan massal diperlukan</div>'
            else:
                message = process_hapus_massal(selected_transactions, user_email)
        elif action == "delete_all":
            if konfirmasi != "YA_ALL":
                message = '<div class="message error">❌ Konfirmasi penghapusan SEMUA transaksi diperlukan</div>'
            else:
                message = process_hapus_semua_transaksi(user_email)
    
    # Ambil data semua transaksi user yang login
    semua_transaksi = get_semua_transaksi_user_advanced(user_email)
    
    return generate_hapus_transaksi_massal_html(user_email, message, semua_transaksi)

def get_semua_transaksi_user_advanced(user_email):
    """Ambil semua transaksi dengan informasi lengkap untuk massal"""
    try:
        semua_transaksi = []
        
        # Ambil semua jenis transaksi sekaligus dengan query lebih efisien
        tables = [
            ("penjualan", "PENJUALAN", "🛍️", "nama_barang", "total_penjualan"),
            ("pembelian", "PEMBELIAN", "🛒", "nama_barang", "total_pembelian"), 
            ("operasional", "OPERASIONAL", "💰", "nama_barang", "total_pengeluaran"),
            ("prive", "PRIVE", "💼", "keterangan", "jumlah"),
            ("modal", "MODAL", "📈", "keterangan", "jumlah")
        ]
        
        for table_name, jenis, icon, nama_field, jumlah_field in tables:
            try:
                result = supabase.table(table_name).select("*").eq("user_email", user_email).execute()
                for item in result.data:
                    item['jenis'] = jenis
                    item['icon'] = icon
                    item['nama_display'] = item.get(nama_field, 'Tidak ada nama')
                    item['jumlah_display'] = f"Rp {item.get(jumlah_field, 0):,}"
                    item['nilai'] = item.get(jumlah_field, 0)
                    item['table_source'] = table_name
                    item['tanggal_formatted'] = item.get('tanggal', '')[:10] if item.get('tanggal') else 'Tanggal tidak tersedia'
                    
                    # Format display untuk UI
                    item['display'] = f"{icon} {jenis}: {item['nama_display']} - {item['jumlah_display']}"
                    
                    semua_transaksi.append(item)
            except Exception as e:
                logger.error(f"❌ Error mengambil {table_name}: {str(e)}")
                continue
        
        # Urutkan berdasarkan tanggal (yang terbaru di atas)
        semua_transaksi.sort(key=lambda x: x.get('tanggal', ''), reverse=True)
        
        logger.info(f"📊 Found {len(semua_transaksi)} transactions for mass operations")
        return semua_transaksi
        
    except Exception as e:
        logger.error(f"❌ Error get transaksi advanced: {str(e)}")
        return []

def process_hapus_massal(selected_transactions, user_email):
    """Process penghapusan transaksi massal - DIPERBAIKI"""
    try:
        if not selected_transactions:
            return '<div class="message error">❌ Tidak ada transaksi yang dipilih</div>'
        
        success_count = 0
        error_count = 0
        deleted_info = []
        
        for transaksi_data in selected_transactions:
            try:
                # Parse data transaksi (format: table_name|transaksi_id)
                parts = transaksi_data.split('|')
                if len(parts) != 2:
                    error_count += 1
                    continue
                
                table_name, transaksi_id = parts
                
                # Dapatkan info transaksi sebelum dihapus untuk laporan
                trans_info = get_transaksi_info(table_name, transaksi_id)
                
                # ✅ BENAR-BENAR HAPUS DARI DATABASE
                delete_result = supabase.table(table_name).delete().eq("id", transaksi_id).execute()
                
                if delete_result.data:
                    success_count += 1
                    if trans_info:
                        deleted_info.append(trans_info)
                    
                    # ✅ HAPUS JUGA JURNAL YANG TERKAIT
                    hapus_jurnal_terkait(table_name, transaksi_id)
                    
                    # ✅ UPDATE PERSEDIAAN JIKA PERLU
                    if table_name == "penjualan":
                        update_persediaan_setelah_hapus_penjualan(transaksi_id)
                    elif table_name == "pembelian":
                        update_persediaan_setelah_hapus_pembelian(transaksi_id)
                        
                else:
                    error_count += 1
                    
            except Exception as e:
                logger.error(f"❌ Error hapus transaksi {transaksi_data}: {str(e)}")
                error_count += 1
                continue
        
        # Buat laporan hasil
        report_html = f'<div class="message success">✅ Penghapusan Massal Selesai!<br>'
        report_html += f'<strong>Berhasil:</strong> {success_count} transaksi<br>'
        report_html += f'<strong>Gagal:</strong> {error_count} transaksi</div>'
        
        # Tampilkan detail transaksi yang berhasil dihapus (maksimal 5)
        if deleted_info:
            report_html += '<div class="deleted-details"><strong>Transaksi yang dihapus:</strong><ul>'
            for info in deleted_info[:5]:
                report_html += f'<li>• {info}</li>'
            if len(deleted_info) > 5:
                report_html += f'<li>• ... dan {len(deleted_info) - 5} transaksi lainnya</li>'
            report_html += '</ul></div>'
        
        logger.info(f"✅ Mass deletion completed: {success_count} success, {error_count} failed")
        return report_html
        
    except Exception as e:
        logger.error(f"❌ Error process hapus massal: {str(e)}")
        return f'<div class="message error">❌ Error penghapusan massal: {str(e)}</div>'

def process_hapus_semua_transaksi(user_email):
    """Hapus SEMUA transaksi user - DIPERBAIKI"""
    try:
        # Ambil semua transaksi user
        semua_transaksi = get_semua_transaksi_user_advanced(user_email)
        
        if not semua_transaksi:
            return '<div class="message warning">ℹ️ Tidak ada transaksi untuk dihapus</div>'
        
        success_count = 0
        error_count = 0
        total_nilai = sum(transaksi.get('nilai', 0) for transaksi in semua_transaksi)
        
        # ✅ HAPUS SEMUA TRANSAKSI PER TABLE
        tables = ["penjualan", "pembelian", "operasional", "prive", "modal"]
        
        for table_name in tables:
            try:
                # Hapus semua transaksi user di table ini
                delete_result = supabase.table(table_name).delete().eq("user_email", user_email).execute()
                
                if delete_result.data:
                    # Hitung berapa yang berhasil dihapus
                    count_before = len(supabase.table(table_name).select("*").eq("user_email", user_email).execute().data)
                    success_count += count_before
                    
            except Exception as e:
                logger.error(f"❌ Error hapus semua dari {table_name}: {str(e)}")
                error_count += 1
        
        # ✅ HAPUS JUGA SEMUA JURNAL USER
        hapus_semua_jurnal_user(user_email)
        
        report_html = f'<div class="message success">🗑️ SEMUA Transaksi Berhasil Dihapus!<br>'
        report_html += f'<strong>Total dihapus:</strong> {success_count} transaksi<br>'
        report_html += f'<strong>Total nilai:</strong> Rp {total_nilai:,}<br>'
        report_html += f'<strong>Gagal:</strong> {error_count} table</div>'
        
        logger.info(f"✅ All transactions deleted for {user_email}: {success_count} success, {error_count} failed")
        return report_html
        
    except Exception as e:
        logger.error(f"❌ Error hapus semua transaksi: {str(e)}")
        return f'<div class="message error">❌ Error hapus semua transaksi: {str(e)}</div>'

def hapus_jurnal_terkait(table_name, transaksi_id):
    """Hapus jurnal yang terkait dengan transaksi yang dihapus"""
    try:
        # Mapping table ke transaksi_type
        table_to_type = {
            "penjualan": "PENJUALAN",
            "pembelian": "PEMBELIAN", 
            "operasional": "OPERASIONAL",
            "prive": "PRIVE",
            "modal": "TAMBAHAN_MODAL"
        }
        
        transaksi_type = table_to_type.get(table_name)
        if transaksi_type:
            # Hapus jurnal dengan transaksi_id dan transaksi_type yang sesuai
            delete_result = supabase.table("jurnal_umum").delete().eq("transaksi_id", transaksi_id).eq("transaksi_type", transaksi_type).execute()
            logger.info(f"✅ Jurnal terkait dihapus: {transaksi_type} - {transaksi_id}")
            
    except Exception as e:
        logger.error(f"❌ Error hapus jurnal terkait: {str(e)}")

def hapus_semua_jurnal_user(user_email):
    """Hapus semua jurnal user"""
    try:
        delete_result = supabase.table("jurnal_umum").delete().eq("user_email", user_email).execute()
        logger.info(f"✅ Semua jurnal user {user_email} dihapus")
    except Exception as e:
        logger.error(f"❌ Error hapus semua jurnal user: {str(e)}")

def update_persediaan_setelah_hapus_penjualan(transaksi_id):
    """Kembalikan persediaan setelah hapus penjualan - DIPERBAIKI"""
    try:
        # Ambil data penjualan yang dihapus
        result = supabase.table("penjualan").select("*").eq("id", transaksi_id).execute()
        if result.data:
            transaksi_data = result.data[0]
            jumlah = transaksi_data.get('jumlah', 0)
            
            # Ambil persediaan saat ini
            persediaan_result = supabase.table("persediaan_terintegrasi").select("*").eq("id", 1).execute()
            if persediaan_result.data:
                persediaan_sekarang = persediaan_result.data[0]['jumlah_persediaan']
                persediaan_baru = persediaan_sekarang + jumlah
                
                # Update persediaan
                supabase.table("persediaan_terintegrasi").update({
                    "jumlah_persediaan": persediaan_baru,
                    "updated_by": "system_hapus_penjualan",
                    "updated_at": datetime.now().isoformat()
                }).eq("id", 1).execute()
                
                logger.info(f"📦 Persediaan dikembalikan setelah hapus penjualan: +{jumlah} ekor")
    except Exception as e:
        logger.error(f"❌ Error update persediaan penjualan: {str(e)}")

def update_persediaan_setelah_hapus_pembelian(transaksi_id):
    """Kurangi persediaan setelah hapus pembelian - DIPERBAIKI"""
    try:
        # Ambil data pembelian yang dihapus
        result = supabase.table("pembelian").select("*").eq("id", transaksi_id).execute()
        if result.data:
            transaksi_data = result.data[0]
            jumlah = transaksi_data.get('jumlah', 0)
            
            # Ambil persediaan saat ini
            persediaan_result = supabase.table("persediaan_terintegrasi").select("*").eq("id", 1).execute()
            if persediaan_result.data:
                persediaan_sekarang = persediaan_result.data[0]['jumlah_persediaan']
                persediaan_baru = max(0, persediaan_sekarang - jumlah)  # Jangan sampai minus
                
                # Update persediaan
                supabase.table("persediaan_terintegrasi").update({
                    "jumlah_persediaan": persediaan_baru,
                    "updated_by": "system_hapus_pembelian",
                    "updated_at": datetime.now().isoformat()
                }).eq("id", 1).execute()
                
                logger.info(f"📦 Persediaan dikurangi setelah hapus pembelian: -{jumlah} ekor")
    except Exception as e:
        logger.error(f"❌ Error update persediaan pembelian: {str(e)}")

def get_transaksi_info(table_name, transaksi_id):
    """Dapatkan informasi transaksi untuk laporan - DIPERBAIKI"""
    try:
        result = supabase.table(table_name).select("*").eq("id", transaksi_id).execute()
        if result.data:
            data = result.data[0]
            
            if table_name == "penjualan":
                return f"🛍️ Penjualan: {data.get('nama_barang', '')} - Rp {data.get('total_penjualan', 0):,}"
            elif table_name == "pembelian":
                return f"🛒 Pembelian: {data.get('nama_barang', '')} - Rp {data.get('total_pembelian', 0):,}"
            elif table_name == "operasional":
                return f"💰 Operasional: {data.get('nama_barang', '')} - Rp {data.get('total_pengeluaran', 0):,}"
            elif table_name == "prive":
                return f"💼 Prive: {data.get('keterangan', '')} - Rp {data.get('jumlah', 0):,}"
            elif table_name == "modal":
                tipe = data.get('tipe', 'MODAL')
                return f"📈 {tipe}: {data.get('keterangan', '')} - Rp {data.get('jumlah', 0):,}"
                
    except Exception as e:
        logger.error(f"❌ Error get transaksi info: {str(e)}")
    
    return f"Transaksi {table_name}#{transaksi_id}"

# ============================================================
# 🔹 GENERATE UNTUK HAPUS MASSAL
# ============================================================
def generate_hapus_transaksi_massal_html(user_email, message, semua_transaksi):
    """Generate HTML untuk halaman hapus transaksi massal"""
    
    # Hitung statistik
    total_transaksi = len(semua_transaksi)
    total_nilai = sum(transaksi.get('nilai', 0) for transaksi in semua_transaksi)
    
    # Generate tabel transaksi dengan checkbox
    transaksi_table = ""
    if semua_transaksi:
        for i, transaksi in enumerate(semua_transaksi):
            transaksi_value = f"{transaksi['table_source']}|{transaksi['id']}"
            transaksi_table += f"""
            <tr class="transaksi-row">
                <td class="checkbox-cell">
                    <input type="checkbox" name="selected_transactions" value="{transaksi_value}" 
                           class="transaksi-checkbox" id="transaksi-{i}">
                </td>
                <td class="icon-cell">{transaksi['icon']}</td>
                <td class="info-cell">
                    <strong>{transaksi['nama_display']}</strong>
                    <div class="transaksi-details">
                        <span class="jenis-badge {transaksi['jenis'].lower()}">{transaksi['jenis']}</span>
                        • {transaksi['jumlah_display']} • 📅 {transaksi['tanggal_formatted']}
                    </div>
                </td>
                <td class="actions-cell">
                    <button type="button" class="btn-quick-delete" 
                            onclick="quickDelete('{transaksi_value}')" 
                            title="Hapus cepat transaksi ini">
                        🗑️
                    </button>
                </td>
            </tr>
            """
    else:
        transaksi_table = """
        <tr>
            <td colspan="4" class="empty-state">
                <h3>📊 Belum ada transaksi</h3>
                <p>Transaksi yang Anda buat akan muncul di sini</p>
                <br>
                <a href="/dashboard" class="btn">🏠 Kembali ke Dashboard</a>
                <a href="/tambah-penjualan" class="btn" style="background: #28a745;">➕ Buat Transaksi Baru</a>
            </td>
        </tr>
        """
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Hapus Transaksi Massal - PINKILANG</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #ffe6e6, #ffcccc);
                padding: 20px;
                min-height: 100vh;
            }}
            
            .container {{
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                border-radius: 15px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                overflow: hidden;
            }}
            
            .header {{
                background: linear-gradient(135deg, #ff4444, #cc0000);
                color: white;
                padding: 25px;
                text-align: center;
            }}
            
            .back-btn {{
                display: inline-block;
                padding: 10px 20px;
                background: rgba(255,255,255,0.2);
                color: white;
                text-decoration: none;
                border-radius: 8px;
                margin-bottom: 15px;
                border: 1px solid rgba(255,255,255,0.3);
                transition: all 0.3s ease;
            }}
            
            .back-btn:hover {{
                background: rgba(255,255,255,0.3);
                transform: translateY(-2px);
            }}
            
            h1 {{
                font-size: 28px;
                margin-bottom: 10px;
            }}
            
            .content {{
                padding: 25px;
            }}
            
            /* Statistics Cards */
            .stats-container {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin: 20px 0;
            }}
            
            .stat-card {{
                background: #f8f9fa;
                padding: 20px;
                border-radius: 10px;
                text-align: center;
                border-left: 4px solid #ff4444;
            }}
            
            .stat-number {{
                font-size: 24px;
                font-weight: bold;
                color: #ff4444;
            }}
            
            .stat-label {{
                font-size: 14px;
                color: #666;
                margin-top: 5px;
            }}
            
            /* Mass Actions */
            .mass-actions {{
                background: #fff3cd;
                border: 2px solid #ffeaa7;
                border-radius: 10px;
                padding: 20px;
                margin: 20px 0;
            }}
            
            .action-buttons {{
                display: flex;
                gap: 10px;
                flex-wrap: wrap;
                margin-top: 15px;
            }}
            
            .btn-mass {{
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                font-size: 14px;
                transition: all 0.3s ease;
            }}
            
            .btn-delete-selected {{
                background: #ff4444;
                color: white;
            }}
            
            .btn-delete-all {{
                background: #dc3545;
                color: white;
            }}
            
            .btn-select-all {{
                background: #6c757d;
                color: white;
            }}
            
            .btn-mass:hover {{
                transform: translateY(-2px);
                opacity: 0.9;
            }}
            
            /* Transactions Table */
            .transactions-table {{
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
                background: white;
                border-radius: 8px;
                overflow: hidden;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            
            .transactions-table th {{
                background: #f8f9fa;
                padding: 15px;
                text-align: left;
                font-weight: 600;
                color: #333;
                border-bottom: 2px solid #dee2e6;
            }}
            
            .transactions-table td {{
                padding: 12px 15px;
                border-bottom: 1px solid #dee2e6;
            }}
            
            .transaksi-row:hover {{
                background: #f8f9fa;
            }}
            
            .checkbox-cell {{
                width: 40px;
            }}
            
            .icon-cell {{
                width: 50px;
                font-size: 18px;
                text-align: center;
            }}
            
            .info-cell {{
                min-width: 300px;
            }}
            
            .actions-cell {{
                width: 80px;
                text-align: center;
            }}
            
            .transaksi-checkbox {{
                transform: scale(1.2);
            }}
            
            .transaksi-details {{
                font-size: 12px;
                color: #666;
                margin-top: 5px;
            }}
            
            .jenis-badge {{
                display: inline-block;
                padding: 2px 8px;
                border-radius: 12px;
                font-size: 10px;
                font-weight: bold;
                color: white;
            }}
            
            .jenis-badge.penjualan {{ background: #28a745; }}
            .jenis-badge.pembelian {{ background: #007bff; }}
            .jenis-badge.operasional {{ background: #ff6b00; }}
            .jenis-badge.prive {{ background: #6f42c1; }}
            .jenis-badge.modal {{ background: #17a2b8; }}
            
            .btn-quick-delete {{
                background: none;
                border: 1px solid #ff4444;
                color: #ff4444;
                padding: 5px 10px;
                border-radius: 4px;
                cursor: pointer;
                transition: all 0.3s ease;
            }}
            
            .btn-quick-delete:hover {{
                background: #ff4444;
                color: white;
            }}
            
            /* Selection Counter */
            .selection-counter {{
                background: #e6f7ff;
                border: 1px solid #91d5ff;
                border-radius: 8px;
                padding: 10px 15px;
                margin: 10px 0;
                font-size: 14px;
                color: #0066cc;
            }}
            
            /* Messages */
            .message {{
                padding: 15px;
                margin: 15px 0;
                border-radius: 8px;
                font-size: 14px;
            }}
            
            .success {{
                background: #d4edda;
                color: #155724;
                border: 1px solid #c3e6cb;
            }}
            
            .error {{
                background: #f8d7da;
                color: #721c24;
                border: 1px solid #f5c6cb;
            }}
            
            .warning {{
                background: #fff3cd;
                color: #856404;
                border: 1px solid #ffeaa7;
            }}
            
            .deleted-details {{
                background: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 15px;
                margin: 10px 0;
                font-size: 13px;
            }}
            
            .deleted-details ul {{
                margin: 10px 0;
                padding-left: 20px;
            }}
            
            .empty-state {{
                text-align: center;
                padding: 40px;
                color: #666;
            }}
            
            .empty-state h3 {{
                margin-bottom: 10px;
                color: #333;
            }}
            
            .btn {{
                display: inline-block;
                padding: 10px 20px;
                background: #666;
                color: white;
                text-decoration: none;
                border-radius: 5px;
                margin: 5px;
                transition: all 0.3s ease;
            }}
            
            .btn:hover {{
                background: #555;
                transform: translateY(-2px);
            }}
            
            @media (max-width: 768px) {{
                .mass-actions {{
                    padding: 15px;
                }}
                
                .action-buttons {{
                    flex-direction: column;
                }}
                
                .btn-mass {{
                    width: 100%;
                }}
                
                .transactions-table {{
                    font-size: 14px;
                }}
                
                .transactions-table td {{
                    padding: 8px 10px;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <!-- Header -->
            <div class="header">
                <a href="/dashboard" class="back-btn">← Kembali ke Dashboard</a>
                <h1>🗑️ Hapus Transaksi Massal</h1>
                <p>Kelola dan Hapus Multiple Transaksi Sekaligus - PINKILANG</p>
            </div>
            
            <!-- Content -->
            <div class="content">
                {message}
                
                <!-- User Info -->
                <div style="text-align: center; margin-bottom: 20px; color: #666;">
                    👋 Anda login sebagai: <strong>{user_email}</strong>
                </div>
                
                <!-- Statistics -->
                <div class="stats-container">
                    <div class="stat-card">
                        <div class="stat-number">{total_transaksi}</div>
                        <div class="stat-label">Total Transaksi</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">Rp {total_nilai:,}</div>
                        <div class="stat-label">Total Nilai</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number" id="selected-count">0</div>
                        <div class="stat-label">Dipilih</div>
                    </div>
                </div>
                
                <!-- Mass Actions -->
                <div class="mass-actions">
                    <h3 style="color: #856404; margin-bottom: 15px;">🚀 Aksi Massal</h3>
                    
                    <div class="selection-counter" id="selection-info">
                        Pilih transaksi yang ingin dihapus dengan mencentang checkbox
                    </div>
                    
                    <form method="POST" id="massForm">
                        <div class="action-buttons">
                            <button type="button" class="btn-mass btn-select-all" onclick="selectAll()">
                                📋 Pilih Semua
                            </button>
                            <button type="button" class="btn-mass btn-select-all" onclick="deselectAll()">
                                ❌ Batal Pilih Semua
                            </button>
                            <button type="submit" class="btn-mass btn-delete-selected" 
                                    name="action" value="delete_selected"
                                    onclick="return confirmMassDelete('selected')">
                                🗑️ Hapus yang Dipilih
                            </button>
                            <button type="submit" class="btn-mass btn-delete-all" 
                                    name="action" value="delete_all"
                                    onclick="return confirmMassDelete('all')">
                                💥 Hapus SEMUA Transaksi
                            </button>
                        </div>
                        
                        <!-- Hidden confirmation fields -->
                        <input type="hidden" name="konfirmasi" id="konfirmasi" value="">
                        
                        <!-- Transactions Table -->
                        <table class="transactions-table">
                            <thead>
                                <tr>
                                    <th class="checkbox-cell">
                                        <input type="checkbox" id="select-all-checkbox" onchange="toggleSelectAll(this)">
                                    </th>
                                    <th class="icon-cell">Icon</th>
                                    <th class="info-cell">Informasi Transaksi</th>
                                    <th class="actions-cell">Aksi</th>
                                </tr>
                            </thead>
                            <tbody>
                                {transaksi_table}
                            </tbody>
                        </table>
                    </form>
                </div>
                
                <!-- Warning -->
                <div class="message warning">
                    <strong>⚠️ PERHATIAN!</strong><br>
                    • Data yang dihapus tidak dapat dikembalikan<br>
                    • Jurnal akuntansi terkait juga akan terhapus otomatis<br>
                    • Persediaan akan disesuaikan untuk transaksi penjualan/pembelian<br>
                    • Hanya transaksi yang Anda buat yang dapat dihapus
                </div>
                
                <!-- Navigation -->
                <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee;">
                    <a href="/dashboard" class="btn">🏠 Dashboard</a>
                    <a href="/jurnal-umum" class="btn" style="background: #6f42c1;">📝 Lihat Jurnal</a>
                </div>
            </div>
        </div>
        
        <script>
            // Selection counter
            function updateSelectionCounter() {{
                const checkboxes = document.querySelectorAll('.transaksi-checkbox:checked');
                const selectedCount = checkboxes.length;
                document.getElementById('selected-count').textContent = selectedCount;
                
                const selectionInfo = document.getElementById('selection-info');
                if (selectedCount > 0) {{
                    selectionInfo.innerHTML = `✅ <strong>${{selectedCount}} transaksi</strong> dipilih untuk dihapus`;
                    selectionInfo.style.background = '#d4edda';
                    selectionInfo.style.border = '1px solid #c3e6cb';
                    selectionInfo.style.color = '#155724';
                }} else {{
                    selectionInfo.innerHTML = 'Pilih transaksi yang ingin dihapus dengan mencentang checkbox';
                    selectionInfo.style.background = '#e6f7ff';
                    selectionInfo.style.border = '1px solid #91d5ff';
                    selectionInfo.style.color = '#0066cc';
                }}
            }}
            
            // Select all functionality
            function toggleSelectAll(source) {{
                const checkboxes = document.querySelectorAll('.transaksi-checkbox');
                checkboxes.forEach(checkbox => {{
                    checkbox.checked = source.checked;
                }});
                updateSelectionCounter();
            }}
            
            function selectAll() {{
                const checkboxes = document.querySelectorAll('.transaksi-checkbox');
                checkboxes.forEach(checkbox => {{
                    checkbox.checked = true;
                }});
                document.getElementById('select-all-checkbox').checked = true;
                updateSelectionCounter();
            }}
            
            function deselectAll() {{
                const checkboxes = document.querySelectorAll('.transaksi-checkbox');
                checkboxes.forEach(checkbox => {{
                    checkbox.checked = false;
                }});
                document.getElementById('select-all-checkbox').checked = false;
                updateSelectionCounter();
            }}
            
            // Quick delete function
            function quickDelete(transaksiValue) {{
                if (confirm('Yakin hapus transaksi ini?\\n\\nData tidak dapat dikembalikan!')) {{
                    // Create a temporary form for quick delete
                    const form = document.createElement('form');
                    form.method = 'POST';
                    form.action = window.location.href;
                    
                    const input1 = document.createElement('input');
                    input1.type = 'hidden';
                    input1.name = 'selected_transactions';
                    input1.value = transaksiValue;
                    
                    const input2 = document.createElement('input');
                    input2.type = 'hidden';
                    input2.name = 'action';
                    input2.value = 'delete_selected';
                    
                    const input3 = document.createElement('input');
                    input3.type = 'hidden';
                    input3.name = 'konfirmasi';
                    input3.value = 'YA';
                    
                    form.appendChild(input1);
                    form.appendChild(input2);
                    form.appendChild(input3);
                    document.body.appendChild(form);
                    form.submit();
                }}
            }}
            
            // Mass delete confirmation
            function confirmMassDelete(type) {{
                const checkboxes = document.querySelectorAll('.transaksi-checkbox:checked');
                const selectedCount = checkboxes.length;
                
                if (type === 'selected' && selectedCount === 0) {{
                    alert('❌ Tidak ada transaksi yang dipilih!');
                    return false;
                }}
                
                let message = '';
                if (type === 'selected') {{
                    message = `Apakah Anda yakin ingin menghapus ${{selectedCount}} transaksi yang dipilih?\\n\\n⚠️ Data tidak dapat dikembalikan!`;
                    document.getElementById('konfirmasi').value = 'YA';
                }} else {{
                    message = `⚠️ ⚠️ ⚠️ PERINGATAN!\\n\\nAnda akan menghapus SEMUA ${{total_transaksi}} transaksi!\\nTotal nilai: Rp {total_nilai:,}\\n\\nTindakan ini TIDAK DAPAT DIBATALKAN!\\nYakin lanjutkan?`;
                    document.getElementById('konfirmasi').value = 'YA_ALL';
                }}
                
                return confirm(message);
            }}
            
            // Initialize
            document.addEventListener('DOMContentLoaded', function() {{
                const checkboxes = document.querySelectorAll('.transaksi-checkbox');
                checkboxes.forEach(checkbox => {{
                    checkbox.addEventListener('change', updateSelectionCounter);
                }});
                updateSelectionCounter();
                
                // Auto hide messages after 5 seconds
                setTimeout(function() {{
                    const messages = document.querySelectorAll('.message');
                    messages.forEach(message => {{
                        message.style.opacity = '0';
                        message.style.transition = 'opacity 0.5s ease';
                        setTimeout(() => message.remove(), 500);
                    }});
                }}, 5000);
            }});
        </script>
    </body>
    </html>
    """
    return html
# ============================================================
# 🔹 ROUTE: Logout
# ============================================================
@app.route("/logout")
def logout():
    session.clear()
    return redirect('/')

# ============================================================
# 🔹 Jalankan Aplikasi
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("🚀 PINKILANG - Fixed Version")
    print("=" * 60)
    print(f"📧 Email: {EMAIL_SENDER}")
    print(f"🔗 Supabase: {SUPABASE_URL}")
    print(f"📊 Database Status: {db_status}")
    print("💡 Buka: http://localhost:5000")
    print("=" * 60)
    
    app.run(debug=True, host="0.0.0.0", port=5000)