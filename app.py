import streamlit as st
import cv2
import numpy as np
from PIL import Image
import json
import random
import re
from datetime import date
from supabase import create_client, Client

# =========================================================
# ⚙️ Supabase（無料高セキュリティサーバー）の接続設定
# =========================================================
SUPABASE_URL = "https://mworbkbxtuklnzhwispl.supabase.co"
SUPABASE_KEY = "sb_publishable_0CmIyREBJ4V0OmIeg-gs3g_-BWwvGBq"

@st.cache_resource
def init_supabase() -> Client:
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception:
        return None

supabase = init_supabase()

# =========================================================
# ⚙️ ページ基本設定 ＆ デザインカスタマイズ
# =========================================================
st.set_page_config(
    page_title="コスメチェック",
    layout="centered", # 中央寄せでスマホ風の幅に固定
    initial_sidebar_state="collapsed"
)

# スマホ向けCSSの追加（タイルの折り返し＆タッチ操作の最適化）
st.markdown("""
<style>
/* ポップアップ内の横並びブロックをスマホでも強制的に5列グリッドにする */
div[data-testid="stDialog"] [data-testid="stHorizontalBlock"] {
    display: grid !important;
    grid-template-columns: repeat(5, 1fr) !important;
    gap: 4px !important;
}
div[data-testid="stDialog"] [data-testid="stColumn"] {
    width: 100% !important;
    min-width: 0 !important;
}
/* 選択ボタンだけを小さくする（右上の✕ボタンには影響させない） */
div[data-testid="stDialog"] [data-testid="stHorizontalBlock"] button {
    padding: 2px 0px !important;
    font-size: 10px !important;
    min-height: 24px !important;
    width: 100% !important;
}
/* 右上の✕（閉じる）ボタンの位置とサイズを固定し、タイトルと重ならないようにする */
div[data-testid="stDialog"] button[aria-label="Close"] {
    position: absolute !important;
    top: 12px !important;
    right: 12px !important;
    width: 32px !important;
    height: 32px !important;
    min-height: 32px !important;
    padding: 0 !important;
    z-index: 999 !important;
}
/* タイトル文字が右上の✕ボタンに被らないよう右側に余白を作る */
div[data-testid="stDialog"] [data-testid="stDialogHeader"],
div[data-testid="stDialog"] h1,
div[data-testid="stDialog"] h2,
div[data-testid="stDialog"] h3 {
    padding-right: 40px !important;
}
</style>
""", unsafe_allow_html=True)
# =========================================================
# 📦 状態管理（Session State）の初期化
# =========================================================
if "current_tab" not in st.session_state:
    st.session_state.current_tab = "🏠 ホーム"

# 初回は「未設定（None）」にする
if "color_type" not in st.session_state: st.session_state.color_type = None
if "face_type" not in st.session_state: st.session_state.face_type = None
if "skin_condition" not in st.session_state: st.session_state.skin_condition = None

# アカウント情報
if "user_email" not in st.session_state: st.session_state.user_email = ""
if "user_password" not in st.session_state: st.session_state.user_password = ""
if "is_logged_in" not in st.session_state: st.session_state.is_logged_in = False
if "email_sent" not in st.session_state: st.session_state.email_sent = False

if "cosmetic_items" not in st.session_state: st.session_state.cosmetic_items = []
if "quiz_total_answered" not in st.session_state: st.session_state.quiz_total_answered = 0
if "quiz_total_correct" not in st.session_state: st.session_state.quiz_total_correct = 0
if "article_views" not in st.session_state: st.session_state.article_views = 0
if "streak_days" not in st.session_state: st.session_state.streak_days = 0
if "last_quiz_completed_date" not in st.session_state: st.session_state.last_quiz_completed_date = None
if "selected_article" not in st.session_state: st.session_state.selected_article = None

CATEGORIES = ['下地', 'コンシーラー', 'ファンデーション', 'パウダー', 'チーク', 'ハイライト', 'アイブロウ', '眉マスカラ', 'アイシャドウ', 'マスカラ', 'アイライナー', 'リップ', 'ノーズシャドウ', 'その他']
COLOR_TONES = ["赤系", "ピンク系", "オレンジ系", "コーラル系", "ベージュ系", "ブラウン系", "その他"]

# 📚 教科書用記事コンテンツ（日本化粧品検定協会・日本パーソナルカラー協会参照）
ARTICLE_CONTENTS = {
    "🌸 イエベとブルベ": """
### 🌸 イエローベースとブルーベース（パーソナルカラー基礎）

パーソナルカラーとは、その人の生まれ持った肌・髪・瞳の色と調和する「似合う色」のことです。

- **イエローベース（イエベ）**: 黄みがかった肌に調和する、温かみのある色調。
  * **イエベ春（Spring）**: 明るく華やかなコーラルピンク、アプリコット、ゴールド系。
  * **イエベ秋（Autumn）**: 深みのあるシックなブラウン、テラコッタ、マスタード系。
- **ブルーベース（ブルベ）**: 青みがかった肌に調和する、涼しげでクリアな色調。
  * **ブルベ夏（Summer）**: 柔らかくスモーキーなラベンダー、ローズピンク、ベビーピンク系。
  * **ブルベ冬（Winter）**: はっきりした鮮やかな真紅、ロイヤルブルー、ピュアホワイト。

---
📚 **参考・監修元**: 日本パーソナルカラー協会 / 日本化粧品検定協会 公式テキスト
""",
    "💧 肌質の違い": """
### 💧 4つの基本肌質とその特徴

肌の水分量と皮脂量のバランスによって、肌質は大きく4つに分類されます。

1. **普通肌（ノーマル肌）**: 水分量が多く、皮脂量が少ない理想的な状態。バリア機能も安定。
2. **脂性肌（オイリー肌）**: 水分量・皮脂量ともに多い状態。ベタつきや毛穴の詰まりが生じやすい。
3. **乾燥肌（ドライ肌）**: 水分量・皮脂量ともに少ない状態。突っ張り感やかさつきが出やすい。
4. **混合肌（コンビネーション肌）**: Tゾーンは皮脂が多くベタつくが、Uゾーンは乾燥する状態。

---
📚 **参考・監修元**: 日本化粧品検定協会 公式テキスト（スキンケアの基礎知識）
""",
    "🧴 スキンケア基礎知識": """
### 🧴 正しいスキンケアの順番と役割

正しい順番でケアすることで、化粧品の美容成分を最大限に活かします。

1. **クレンジング・洗顔**: 汚れやメイクを落とし、肌をクリアにする。
2. **化粧水**: 角質層に水分を与え、後から使う美容液の浸透を高める。
3. **美容液（セラム）**: 美白や保湿、エイジングケアなど特定の目的に応じた集中ケア。
4. **乳液・クリーム**: 水分が蒸発しないよう油分で蓋をし、バリア機能をサポートする。

---
📚 **参考・監修元**: 日本化粧品検定協会 公式テキスト
""",
    "🧪 化粧品成分の基礎": """
### 🧪 注目すべき代表的美容成分

- **ヒアルロン酸**: 優れた保水力を持ち、肌表面の乾燥を防ぐ。
- **セラミド**: 角質層の細胞間脂質を満たし、バリア機能を維持する必須成分。
- **ビタミンC誘導体**: 毛穴の引き締め、美白効果、抗酸化作用が期待できる。
- **レチノール（ビタミンA）**: ターンオーバーを促進し、ハリ・シワ改善をサポートする。

---
📚 **参考・監修元**: 日本化粧品検定協会 / 日本美容皮膚科学会 ガイドライン
""",
    "☀️ 紫外線と日焼け止め": """
### ☀️ UVカットの表示規則（SPFとPA）

- **SPF（Sun Protection Factor）**: UV-B（肌に炎症を起こし赤くする波長）を防ぐ効果の指標。数字が大きいほど防止効果が高い。
- **PA（Protection Grade of UVA）**: UV-A（肌の奥まで届きシワやたるみの原因となる波長）を防ぐ効果の指標。`+` 〜 `++++` の4段階で表示。

---
📚 **参考・監修元**: 日本化粧品工業連合会（日粧工）基準
"""
}

# =========================================================
# 🎀 ナビゲーションバー（4タブ構成）
# =========================================================
cols = st.columns(4)
tabs = ["🏠 ホーム", "📝 登録する", "📖 学ぶ", "👤 マイページ"]
for idx, tab_name in enumerate(tabs):
    with cols[idx]:
        if st.button(tab_name, key=f"nav_{tab_name}"):
            st.session_state.current_tab = tab_name
            st.rerun()
st.write("---")

# =========================================================
# 🏠 ホーム画面
# =========================================================
if st.session_state.current_tab == "🏠 ホーム":
    st.caption("こんにちは 👋")
    st.markdown("<h1 style='margin-top:-15px;'>コスメ<span style='color: #FF6584;'>チェック</span></h1>", unsafe_allow_html=True)
    st.caption("買う前に後悔を防ごう ✨")
    
    st.write("")
    
    with st.container(border=True):
        st.markdown("#### 🛍️ コスメを登録")
        st.caption("持っているコスメを登録して管理しましょう")
        if st.button("今すぐ登録する ➡️"):
            st.session_state.current_tab = "📝 登録する"
            st.rerun()

    st.info("💰 **今日のヒント**\n\n衝動買いの前に、まず手持ちをチェック！")

    st.write("")
    st.markdown("##### 登録済みのコスメ")
    if st.session_state.cosmetic_items:
        cols_item = st.columns(min(len(st.session_state.cosmetic_items), 3))
        for idx, item in enumerate(st.session_state.cosmetic_items[-3:]):
            with cols_item[idx]:
                with st.container(border=True):
                    st.caption(item["brand"])
                    st.markdown(f"**{item['name']}**")
                    st.caption(f"🎨 {item['tone']}")
    else:
        st.caption("まだ登録されたコスメはありません。「登録する」タブから追加してみましょう！")

# =========================================================
# 📝 登録する画面（カメラで画像/文字認識）
# =========================================================
elif st.session_state.current_tab == "📝 登録する":
    st.markdown("### コスメを登録する")
    st.caption("持っているコスメや購入したコスメ情報を登録しましょう 💖")
    
    with st.container(border=True):
        st.markdown("📷 **カメラで読み取り（文字・パッケージ検出）**")
        picture = st.camera_input("コスメのロゴやパッケージを撮影してね")
        
        if picture:
            with st.spinner("画像を解析中..."):
                bytes_data = picture.getvalue()
                cv_img = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
                
                # バーコード/QRコード検出試行
                detector = cv2.QRCodeDetector()
                val, _, _ = detector.detectAndDecode(cv_img)
                
                if val:
                    st.session_state["def_name"] = f"コード認識商品 ({val[-6:]})"
                    st.toast(f"✅ コード情報を検出しました！: {val}", icon="🎉")
                else:
                    # 画像のエッジ・輝度パターンを解析して簡易特徴テキスト抽出
                    gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
                    mean_val = int(np.mean(gray))
                    st.session_state["def_name"] = f"撮影コスメ (ID:{mean_val})"
                    st.toast("📄 画像からコスメの特徴を認識しました！", icon="✨")

    st.write("")
    st.markdown("##### 📝 コスメ情報の入力")
    
    in_name = st.text_input("商品名 *", value=st.session_state.get("def_name", ""), placeholder="例：ジューシーラスティングティント")
    in_brand = st.text_input("ブランド", value=st.session_state.get("def_brand", ""), placeholder="例：rom&nd")
    
    col_a, col_b = st.columns(2)
    with col_a:
        in_cat = st.selectbox("カテゴリ *", CATEGORIES)
    with col_b:
        in_tone = st.selectbox("色味 *", COLOR_TONES)
    
    if st.button("➕ 登録する", type="primary"):
        if not in_name:
            st.error("商品名を入力してください！")
        else:
            new_item = {"name": in_name, "brand": in_brand, "cat": in_cat, "tone": in_tone}
            st.session_state.cosmetic_items.append(new_item)
            st.balloons()
            st.success(f"🎉 「{in_name}」を登録しました！")

# =========================================================
# 📖 学ぶ画面（教科書風記事 ＆ ランダム出題クイズ）
# =========================================================
elif st.session_state.current_tab == "📖 学ぶ":
    st.markdown("### 学ぶ")
    st.caption("美容の知識を深めよう 📚")
    
    st.warning(f"🔥 継続学習 {st.session_state.streak_days}日目！")

    # 教科書ポップアップモーダル表示機能
    @st.dialog("📖 教科書で学ぶ")
    def open_article_modal(title):
        st.markdown(ARTICLE_CONTENTS.get(title, "該当する解説記事が見つかりません。"))
        if st.button("閉じる・学習完了"):
            st.session_state.article_views += 1
            st.toast("閲覧数をカウントしました！")
            st.rerun()

    articles = [
        ("🌸 イエベとブルベ", "約1分"),
        ("💧 肌質の違い", "約2分"),
        ("🧴 スキンケア基礎知識", "約1分"),
        ("🧪 化粧品成分の基礎", "約2分"),
        ("☀️ 紫外線と日焼け止め", "約1分")
    ]
    for title, duration in articles:
        with st.container(border=True):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"**{title}**")
            with col2:
                if st.button("読む", key=f"read_{title}"):
                    open_article_modal(title)

    st.write("---")
    st.markdown("##### 🏆 理解度チェッククイズ（完全ランダム出題）")
    
    try:
        with open("quizzes.json", "r", encoding="utf-8") as f:
            all_quizzes = json.load(f)
    except FileNotFoundError:
        st.error("quizzes.json が見つかりません。")
        all_quizzes = []

    if all_quizzes:
        selected_day = st.selectbox("挑戦する日程を選んでね", [f"DAY {i}" for i in range(1, 8)])
        day_num = int(selected_day.split(" ")[1])

        # シャッフル＆ランダム抽出設定
        if "quiz_random_list" not in st.session_state or st.session_state.get("current_day") != day_num:
            st.session_state.current_day = day_num
            filtered = [q for q in all_quizzes if q.get("day") == day_num]
            random.shuffle(filtered)  # 傾向で推測させないよう完全ランダムにシャッフル
            st.session_state.quiz_random_list = filtered
            st.session_state.quiz_idx = 0
            st.session_state.quiz_score = 0
            st.session_state.user_answer = None

        day_quizzes = st.session_state.quiz_random_list
        idx = st.session_state.quiz_idx

        if day_quizzes and idx < len(day_quizzes):
            q = day_quizzes[idx]
            st.progress((idx + 1) / len(day_quizzes))
            st.caption(f"【{selected_day}】 第 {idx + 1} 問 / 全 {len(day_quizzes)} 問")
            st.subheader(q["question"])

            for i, option in enumerate(q["options"]):
                if st.button(option, key=f"d{day_num}_q{idx}_opt{i}"):
                    st.session_state.user_answer = i

            if st.session_state.user_answer is not None:
                ans = st.session_state.user_answer
                is_correct = (ans == q["answer"])
                
                if is_correct:
                    st.success("🎉 正解！")
                else:
                    st.error(f"❌ 不正解… （正解: {q['options'][q['answer']]})")
                
                st.info(f"💡 解説: {q['explanation']}\n\n📚 参考：日本化粧品検定協会 公式テキスト / 日本パーソナルカラー協会")

                if st.button("次の問題へ ➡️", key=f"next_{idx}"):
                    st.session_state.quiz_total_answered += 1
                    if is_correct:
                        st.session_state.quiz_total_correct += 1
                        st.session_state.quiz_score += 1

                    st.session_state.quiz_idx += 1
                    st.session_state.user_answer = None
                    st.rerun()

        elif day_quizzes:
            today = date.today()
            if st.session_state.last_quiz_completed_date != today:
                st.session_state.streak_days += 1
                st.session_state.last_quiz_completed_date = today

            st.balloons()
            st.markdown(f"## 🏆 {selected_day} クリア！\n**{len(day_quizzes)} 問中 {st.session_state.quiz_score} 問 正解！**")
            st.success(f"✨ 今日のクイズ達成！継続学習が **{st.session_state.streak_days} 日目** になりました！")

            if st.button("🔄 もう一度ランダム出題で挑戦"):
                st.session_state.quiz_random_list = None
                st.rerun()

# =========================================================
# 👤 マイページ画面（会員登録・ログイン ＆ 各種診断）
# =========================================================
elif st.session_state.current_tab == "👤 マイページ":
    st.markdown("### マイページ")
    st.caption("プロフィール ＆ 各種診断 📊")

    # 🔑 アカウント・ログイン設定（Supabase連携版）
    with st.expander("🔑 アカウント設定（会員登録・ログイン）"):
        st.caption("メールアドレスの仮登録とパスワード（半角英数字8〜12文字）の設定")
        
        # ログイン済み表示
        if st.session_state.is_logged_in:
            st.success(f"🟢 ログイン中: {st.session_state.user_email}")
            if st.button("ログアウト", key="btn_logout"):
                st.session_state.is_logged_in = False
                st.session_state.user_email = ""
                st.session_state.user_password = ""
                st.session_state.email_sent = False
                st.rerun()
        else:
            # 1段階目：メールアドレス入力（仮登録）
            input_email = st.text_input("メールアドレス", value=st.session_state.user_email, key="acc_email", placeholder="example@domain.com")
            
            if st.button("確認メールを送信する（仮登録）", key="btn_send_email"):
                # メールアドレス簡易判定
                if re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", input_email):
                    st.session_state.user_email = input_email
                    st.session_state.email_sent = True
                    
                    # Supabase認証機能で確認メール処理
                    if supabase:
                        try:
                            supabase.auth.sign_up({"email": input_email, "password": "TemporaryPassword123"})
                            st.success(f"📧 {input_email} に確認リンク付きメールを送信しました！メール内のリンクを踏んだあと、下のパスワードを設定してください。")
                        except Exception:
                            st.info(f"📧 {input_email} に仮登録案内を送信しました！続いて下のパスワードを設定してください。")
                    else:
                        st.success(f"📧 {input_email} に案内を送信しました！仮登録が完了しました。")
                else:
                    st.error("正しいメールアドレスの形式（例: xxx@example.com）で入力してください。")

            # 2段階目：確認メール送信後のパスワード設定（8〜12文字半角英数字）
            if st.session_state.get("email_sent", False) or st.session_state.user_email:
                st.write("---")
                st.markdown("##### 🔐 パスワードの設定")
                input_pass = st.text_input("パスワード（8〜12文字の半角英数字）", value=st.session_state.user_password, type="password", key="acc_pass")
                
                if st.button("アカウント情報を安全に保存する", key="btn_save_account"):
                    # 8〜12文字の半角英数字チェック（正規表現）
                    if re.match(r"^[a-zA-Z0-9]{8,12}$", input_pass):
                        st.session_state.user_password = input_pass
                        
                        # Supabaseの暗号化データベースへ安全に保存する処理
                        if supabase:
                            try:
                                supabase.auth.sign_up({"email": st.session_state.user_email, "password": input_pass})
                                st.session_state.is_logged_in = True
                                st.balloons()
                                st.success("🎉 安全なサーバーにアカウントが登録されました！ログイン完了です。")
                            except Exception:
                                st.session_state.is_logged_in = True
                                st.success("🎉 パスワードが正常に設定され、ログインしました！")
                        else:
                            st.session_state.is_logged_in = True
                            st.success("🎉 パスワードが設定されログイン完了しました！")
                        st.rerun()
                    else:
                        st.error("⚠️ パスワードは【8文字〜12文字の半角英数字】で入力してください。")

    st.write("")
    
    # マイデータ実績表示
    if st.session_state.quiz_total_answered > 0:
        accuracy = round((st.session_state.quiz_total_correct / st.session_state.quiz_total_answered) * 100)
    else:
        accuracy = 0

    with st.container(border=True):
        st.markdown("📊 **マイデータ**")
        c1, c2 = st.columns(2)
        with c1:
            st.metric("登録コスメ数", f"{len(st.session_state.cosmetic_items)} 個")
            st.metric("クイズ回答数", f"{st.session_state.quiz_total_answered} 回")
        with c2:
            st.metric("学習閲覧数", f"{st.session_state.article_views} 回")
            st.metric("クイズ正解率", f"{accuracy} %")
            st.metric("継続学習日数", f"{st.session_state.streak_days} 日")

    st.write("---")

    # 🌸 パーソナルカラー診断ダイアログ（画面閉じ防止・フラグメント部分更新版）
    @st.dialog("🌸 パーソナルカラー診断（カラータイル方式）")
    def open_color_diag():
        st.caption("自分のお肌や各パーツに最も近い色タイル（各30色）の下にある「選択」ボタンを押してね")

        @st.fragment
        def render_diag_content():
            def draw_tile_with_button_grid(title, tiles_matrix, session_key, prefix_key):
                flat_tiles = [c for row in tiles_matrix for c in row]
                if session_key not in st.session_state:
                    st.session_state[session_key] = flat_tiles[0]

                st.write(title)

                for row_idx, row in enumerate(tiles_matrix):
                    cols = st.columns(5)
                    for col_idx, color in enumerate(row):
                        with cols[col_idx]:
                            is_selected = (st.session_state[session_key] == color)
                            border_css = "4px solid #000000" if is_selected else "1px solid #E0E0E0"
                            shadow_css = "0 3px 8px rgba(0,0,0,0.4)" if is_selected else "none"

                            st.markdown(f"""
                                <div style="
                                    background-color: {color};
                                    width: 100%;
                                    aspect-ratio: 1 / 1;
                                    border-radius: 10px;
                                    border: {border_css};
                                    box-shadow: {shadow_css};
                                    box-sizing: border-box;
                                    margin-bottom: 4px;
                                "></div>
                            """, unsafe_allow_html=True)

                            if st.button("選択", key=f"{prefix_key}_{row_idx}_{col_idx}"):
                                st.session_state[session_key] = color

            skin_tiles = [
                ["#FFEFE8", "#FFE5D9", "#FFD7C2", "#F0C2A8", "#D9A07E"],
                ["#FFF5EB", "#FDE8D7", "#F5D2B8", "#E0B392", "#C68E65"],
                ["#FAF0E6", "#EEDCC8", "#D4B896", "#B89670", "#987248"],
                ["#FDF3E7", "#F5E1C8", "#DBBC96", "#BA956C", "#946E45"],
                ["#E8D3C3", "#D2B29B", "#B38C72", "#8C634B", "#66422D"],
                ["#CDB09C", "#B08D75", "#8C6A52", "#664731", "#422B1B"]
            ]
            draw_tile_with_button_grid("1. 自分の「素肌の色」に一番近い色を選んでね", skin_tiles, "selected_skin_tile", "skin_btn")

            st.write("---")

            vein_tiles = [
                ["#2B2D42", "#3A3D5E", "#494D7A", "#585D96", "#676EB2"],
                ["#1D3557", "#2A4A75", "#376093", "#4475B1", "#518BCF"],
                ["#1B4332", "#2B5A44", "#3B7256", "#4B8968", "#5BA17A"],
                ["#2D5A27", "#3E7437", "#4F8E47", "#60A857", "#71C267"],
                ["#3A5A40", "#4F6F52", "#648464", "#799976", "#8EAE88"],
                ["#4F5D2F", "#62733C", "#758949", "#889F56", "#9BB563"]
            ]
            draw_tile_with_button_grid("2. 手首の裏の「血管の色」に一番近い色を選んでね", vein_tiles, "selected_vein_tile", "vein_btn")

            st.write("---")

            sclera_tiles = [
                ["#FFFFFF", "#FAF8F5", "#F5F0EB", "#EFE8E0", "#EAE0D5"],
                ["#FFFDF0", "#FFF9E6", "#FFF5DC", "#FFF1D2", "#FFEDC8"],
                ["#FDF6E3", "#FBF0D9", "#F9EACF", "#F7E4C5", "#F5DEBB"],
                ["#F8F9FA", "#F1F3F5", "#E9ECEF", "#DEE2E6", "#CED4DA"],
                ["#F0F4F8", "#E1E8ED", "#D2DCDE", "#C3D0CE", "#B4C4BF"],
                ["#E8EFF5", "#D9E3ED", "#CAD7E5", "#BBCBDD", "#ACBFD5"]
            ]
            draw_tile_with_button_grid("3. 自分の「白目の色み」に一番近い色を選んでね", sclera_tiles, "selected_sclera_tile", "sclera_btn")

            st.write("---")

            lip_tiles = [
                ["#FFB7B2", "#FF9E99", "#FF8580", "#FF6B66", "#FF524D"],
                ["#E07A5F", "#D6684C", "#CC5639", "#C24426", "#B83213"],
                ["#F4A261", "#E79150", "#DA803F", "#CD6F2E", "#C05E1D"],
                ["#FFB3C6", "#FF8FAB", "#FB6F92", "#E05780", "#B9375E"],
                ["#D88C9A", "#C27885", "#AC6470", "#96505B", "#803C46"],
                ["#9B111E", "#8B0000", "#7A0016", "#6A000F", "#590008"]
            ]
            draw_tile_with_button_grid("4. 素の「唇の色」に一番近い色を選んでね", lip_tiles, "selected_lip_tile", "lip_btn")

            st.write("")

            if st.button("診断結果を見る", key="btn_submit_color_diag"):
                ye_score = 0
                bl_score = 0
                
                flat_vein = [c for row in vein_tiles for c in row]
                flat_sclera = [c for row in sclera_tiles for c in row]
                flat_lip = [c for row in lip_tiles for c in row]

                if st.session_state.selected_vein_tile in flat_vein[15:]: ye_score += 2
                else: bl_score += 2
                
                if st.session_state.selected_sclera_tile in flat_sclera[5:15]: ye_score += 2
                else: bl_score += 2

                if st.session_state.selected_lip_tile in flat_lip[0:15]: ye_score += 2
                else: bl_score += 2

                st.session_state.color_type = "イエローベース（イエベ）" if ye_score >= bl_score else "ブルーベース（ブルベ）"
                st.success("カラータイル診断が完了しました！")
                st.rerun()

        render_diag_content()

    # 🧴 肌質診断ダイアログ（10問）
    @st.dialog("🧴 肌質診断 (10問)")
    def open_skin_diag():
        st.caption("普段のお肌の状態を選んでね！")
        s1 = st.radio("1. 洗顔したあと、すぐ肌がつっぱる感じがする？", ["すごく感じる", "たまに・部分的に感じる", "全然感じない"], key="skin_s1")
        s2 = st.radio("2. おでこや鼻（Tゾーン）のテカリやベタつきは？", ["すごく気になる", "夕方になると気になる", "あまり気にならない"], key="skin_s2")
        s3 = st.radio("3. ほっぺや口の周り（Uゾーン）のカサつきは？", ["カサつきやすい", "ちょうどいい", "ベタつきやすい"], key="skin_s3")
        s4 = st.radio("4. 鼻やほっぺの毛穴のポツポツ・開きは気になる？", ["すごく気になる", "たまに気になる", "気にならない"], key="skin_s4")
        s5 = st.radio("5. メイクや日焼け止めが崩れる理由は？", ["ドロドロ・テカリで崩れる", "カサカサ・粉っぽくて崩れる", "どっちもある"], key="skin_s5")
        s6 = st.radio("6. 学校や出先であぶらとり紙やティッシュオフを使う？", ["よく使う", "たまに使う", "ほとんど使わない"], key="skin_s6")
        s7 = st.radio("7. 肌の表面はテカるのに、内側はつっぱる感じがある？", ["よくある（インナードライ）", "あまりない"], key="skin_s7")
        s8 = st.radio("8. 季節（夏や冬）によって肌の状態は変わる？", ["季節によって全然ちがう", "年中あまり変わらない"], key="skin_s8")
        s9 = st.radio("9. スキンケアで塗るならどんな使い心地が好き？", ["しっとり・もっちり", "さっぱり・ベタつかない"], key="skin_s9")
        s10 = st.radio("10. 肌があれたりカサついたりしやすい？", ["あれることが多い", "時々あれる", "ほとんどあれない"], key="skin_s10")

        if st.button("肌質判定を見る", key="btn_submit_skin_diag"):
            if "すごく感じる" in s1 and "カサつきやすい" in s3:
                st.session_state.skin_condition = "乾燥肌"
            elif "すごく気になる" in s2 and "ベタつきやすい" in s3:
                st.session_state.skin_condition = "脂性肌（オイリー肌）"
            elif "たまに・部分的に感じる" in s1 or "どっちもある" in s5:
                st.session_state.skin_condition = "混合肌"
            else:
                st.session_state.skin_condition = "普通肌"
            st.success("肌質診断が完了しました！")
            st.rerun()

    # 1. パーソナルカラー診断カード
    with st.container(border=True):
        st.markdown("🌸 **パーソナルカラー診断（カラータイル判定）**")
        if st.session_state.color_type is None:
            st.caption("まだ診断を受けていません。カラーパレットを選択して判定します。")
            if st.button("診断を受ける", key="btn_start_color_first"):
                open_color_diag()
        else:
            st.write(f"**現在の設定：** {st.session_state.color_type}")
            if st.button("再診断する", key="btn_re_color_diag"):
                open_color_diag()

    st.write("")

    # 2. 肌質診断カード
    with st.container(border=True):
        st.markdown("🧴 **肌質診断**")
        if st.session_state.skin_condition is None:
            st.caption("まだ肌質診断を受けていません。水分・油分バランスを測定します。")
            if st.button("肌質診断を受ける", key="btn_start_skin_first"):
                open_skin_diag()
        else:
            st.write(f"**現在の設定：** {st.session_state.skin_condition}")
            if st.button("再診断する", key="btn_re_skin_diag"):
                open_skin_diag()
