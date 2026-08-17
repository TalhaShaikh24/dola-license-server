# 🚀 Free Online Deployment Guide (100% Free 24/7 Hosting)

Aapka **License Server & Super Admin Portal** free me online host karne ke liye sabse best aur simple tareeqe ye hain:

---

## 🌟 Option 1: Render.com (Recommended - Sabse Aasan & Free 24/7)

Render.com par Python FastAPI server 100% Free host ho jata hai aur aapko ek permanent **HTTPS link** (jaise `https://dola-license-server.onrender.com`) mil jata hai.

### Step-by-Step 2-Minute Setup:
1. **GitHub par Code Upload karein**:
   - [github.com](https://github.com) par login karein aur ek new repository banayein (e.g. `dola-license-server`).
   - Apne `server/` folder ka code GitHub repo me push / upload kar dein.

2. **Render.com par Login karein**:
   - [https://render.com](https://render.com) par jayein aur GitHub se **Sign Up / Log In** karein.

3. **New Web Service banayein**:
   - **"New +"** button par click karein -> **"Web Service"** select karein.
   - Apni GitHub repository choose karein.

4. **Settings Fill karein**:
   - **Name**: `dola-license-server` (ya koi bhi name)
   - **Region**: Singapore / Frankfurt / Oregon (Koi bhi)
   - **Branch**: `main`
   - **Root Directory**: `server`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements_server.txt`
   - **Start Command**: `uvicorn server:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: **Free** ($0 / month)

5. **"Deploy Web Service"** par click karein!
   - 1 se 2 minute me aapka server live ho jayega aur aapko aapka public URL mil jayega, jaise:
     `https://dola-license-server.onrender.com`

---

## 🌟 Option 2: Koyeb.com / Railway (Alternative Free Container)
1. [koyeb.com](https://www.koyeb.com) par free account banayein.
2. "Create Service" -> "GitHub" -> Choose repo.
3. Automatically Dockerfile detect karke 1-click me deploy kar dega.

---

## 🌟 Option 3: Instant Free Cloudflare Tunnel / Ngrok (Bina kisi cloud account ke)
Agar aap chahte hain ki aapke apne PC par server chale aur bahar ke users ke liye free public link ban jaye:
1. Terminal me run karein:
   ```powershell
   npx cloudflared tunnel --url http://localhost:8000
   ```
2. Cloudflare aapko free link de dega (e.g. `https://xxxx.trycloudflare.com`).

---

## 🔗 Client App ko Online URL se Connect Kaise Karein:

Jab aapka server live ho jaye (e.g. `https://dola-license-server.onrender.com`):

### Tareeqa 1: `license_config.json` me URL daal dein
Workspace me `license_config.json` file banayein ya edit karein:
```json
{
  "server_url": "https://dola-license-server.onrender.com"
}
```

### Tareeqa 2: Desktop App ke andar se:
1. Desktop app start karein.
2. **"Settings / Device"** tab me jayein.
3. Apna Render online URL paste karein aur **"Save Server URL"** par click karein.

---

## 👑 Super Admin Dashboard Online Access:
Aap kisi bhi mobile ya laptop ke browser me apna link open karke users approve kar sakte hain:
- **URL**: `https://dola-license-server.onrender.com/admin`
- **Username**: `admin`
- **Password**: `admin123`
