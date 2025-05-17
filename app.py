import streamlit as st
from yt_dlp import YoutubeDL
import tempfile # 一時ディレクトリを作成するために使用
import os # ファイルパスの操作に使用
import re # ファイル名を安全にするために使用


# --- ヘルパー関数 ---
def sanitize_filename(filename):
    """ファイル名として安全な文字列に変換する"""
    # Windowsで使えない文字: < > : " / \ | ? *
    # macOS/Linuxで使えない文字: /
    # その他、制御文字なども除去し、アンダースコアに置き換える
    sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', filename)
    # 長すぎるファイル名を短縮 (例: 200文字まで)
    return sanitized[:200]

# --- Streamlit UI ---
st.set_page_config(page_title="YouTube Downloader", layout="centered") # ページの基本設定
# 動画ファイルのURL（例: Streamlitが提供するサンプル動画）
video_url = "static/12421436_1280_720_30fps.mp4"

# CSSとHTMLをst.markdownで埋め込む
st.markdown(
    """
    <style>
    /* Streamlitのメインアプリコンテナのデフォルト背景を透明にする */
    .stApp {{
        background: transparent;
    }}

    /* ヘッダーの背景も透明にする（任意） */
    .stApp > header {{
        background-color: transparent;
    }}

    /* --- テキスト中央揃えスタイル --- */
    h1, h2, h3, h4, h5, h6, p, li, .stMarkdown, .stText, .stAlert, .stMetricLabel, .stMetricValue {{
        text-align: center !important; /* !important で他のスタイルを上書き */
    }}
    
    /* ボタンを中央に配置したい場合 (st.columnsを使わない場合) */
    div.stButton > button {{
        display: block;
        margin: 0 auto;
    }}
    
    /* コンテンツエリアの可読性を上げるためのスタイル（任意） */
    /*
    .main .block-container {{
        background-color: rgba(0, 0, 0, 0.3); /* 半透明の黒背景 */
        padding: 2rem;
        border-radius: 0.5rem;
        color: white; /* 文字色を白に */
    }}
    */
    /* 特定の要素だけ文字色を変える場合 */
    h1, h2, h3, h4, h5, h6 {{
    color: #f0f2f6; /* 明るめの色 */
    }}
    p, li, .stMarkdown, .stText {{
        color: #e0e0e0; /* やや明るめの色 */
    }}

    </style>
    """
    st.markdown(unsafe_allow_html=True)
)

# まずログインボタンを表示し、ユーザーにログインを促す
if not st.user.is_logged_in: # ここでエラーが発生している可能性
    # st.title() や st.header() の代わりに st.markdown を使用
    st.title("YouTube 動画ダウンローダー")
    st.write("お好きなYouTube動画をダウンロードできます。まずはログインから")
    if st.button("ログイン"): # secrets.toml の [auth] セクションか、指定したプロバイダでログイン
        st.login() # st.login() にプロバイダ名を渡すことも可能
    st.stop() # ログインしていない場合は以降の処理を停止

# --- ここから下はログイン済みユーザー向けの処理 ---
st.write(f"ようこそ、{st.user.name} さん！") # st.user.name などもログイン後でないと使えない

st.title("YouTube 動画ダウンローダー")
st.write("お好きなYouTube動画をダウンロードできます。URLを入力し、形式を選択してください。")

# URL入力欄
video_url = st.text_input("YouTube動画のURLを入力してください:", placeholder="例: https://www.youtube.com/watch?v=...")

# ダウンロード形式の選択
# yt-dlpのオプションに合わせて選択肢を用意
format_options = {
    "MP4 (最高画質)": {"format_id": "mp4_best", "ext": "mp4"},
    "M4A (音声のみ - 高音質)": {"format_id": "m4a_best_audio", "ext": "m4a"},
    "MP3 (音声のみ - 標準音質)": {"format_id": "mp3_best_audio", "ext": "mp3"},
    "MP4 (720p)": {"format_id": "mp4_720p", "ext": "mp4"},
    "MP4 (360p)": {"format_id": "mp4_360p", "ext": "mp4"},
}
selected_format_label = st.selectbox(
    "ダウンロードする形式を選択してください:",
    options=list(format_options.keys()),
    index=0 # デフォルトでMP4 (最高画質) を選択
)

# ダウンロードボタン
if st.button("📥 ダウンロード開始", type="primary"):
    if not video_url:
        st.warning("⚠️ URLが入力されていません。")
    else:
        try:
            st.info("ℹ️ 動画情報の取得とダウンロード準備を開始します...")

            chosen_format = format_options[selected_format_label]
            file_extension = chosen_format["ext"]

            # yt-dlpのオプション設定
            ydl_opts = {
                'noplaylist': True, # プレイリストの場合は最初の動画のみダウンロード
                'nocheckcertificate': True,
                'quiet': True, # ログ出力を抑制
                # 'progress_hooks': [lambda d: st.text(f"Status: {d.get('status', '')}, Progress: {d.get('_percent_str', 'N/A')}")], # 詳細な進捗表示は複雑になるため省略
            }

            # 形式ごとのオプション設定
            if chosen_format["format_id"] == "mp4_best":
                ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
                ydl_opts['merge_output_format'] = 'mp4'
            elif chosen_format["format_id"] == "m4a_best_audio":
                ydl_opts['format'] = 'bestaudio[ext=m4a]/bestaudio'
            elif chosen_format["format_id"] == "mp3_best_audio":
                ydl_opts['format'] = 'bestaudio/best'
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192', # 192kbps
                }]
            elif chosen_format["format_id"] == "mp4_720p":
                ydl_opts['format'] = 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best[height<=720]'
                ydl_opts['merge_output_format'] = 'mp4'
            elif chosen_format["format_id"] == "mp4_360p":
                ydl_opts['format'] = 'bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[height<=360][ext=mp4]/best[height<=360]'
                ydl_opts['merge_output_format'] = 'mp4'

            # 一時ディレクトリを作成して、そこにダウンロードファイルを保存
            with tempfile.TemporaryDirectory() as tmpdir:
                # 動画のタイトルを取得してファイル名に使用
                try:
                    with YoutubeDL({'quiet': True, 'skip_download': True, 'noplaylist': True, 'nocheckcertificate': True}) as ydl_info:
                        info_dict = ydl_info.extract_info(video_url, download=False)
                        video_title = sanitize_filename(info_dict.get('title', 'downloaded_video'))
                except Exception as title_e:
                    st.warning(f"動画タイトルの取得に失敗しました。デフォルトのファイル名を使用します。エラー: {str(title_e)}")
                    video_title = "downloaded_video"

                output_filename_template = os.path.join(tmpdir, f"{video_title}.%(ext)s")
                ydl_opts['outtmpl'] = output_filename_template

                st.write(f"⏳ 「{video_title}」を {selected_format_label} 形式でダウンロード中です...")

                with YoutubeDL(ydl_opts) as ydl:
                    ydl.download([video_url]) # ダウンロード実行

                # ダウンロードされたファイルを見つける
                downloaded_file_path = None
                # yt-dlpは指定した拡張子とは異なる拡張子で保存することがあるため、
                # 実際に保存されたファイルを探す
                # 最も可能性の高いファイル名で探す
                expected_final_filename = f"{video_title}.{file_extension}"
                possible_path = os.path.join(tmpdir, expected_final_filename)

                if os.path.exists(possible_path):
                    downloaded_file_path = possible_path
                else: # 見つからない場合はディレクトリ内の最初のファイル（形式が違う場合がある）
                    files_in_tmpdir = os.listdir(tmpdir)
                    if files_in_tmpdir:
                        downloaded_file_path = os.path.join(tmpdir, files_in_tmpdir[0])
                        # 実際の拡張子に合わせてファイル名を調整
                        actual_extension = os.path.splitext(files_in_tmpdir[0])[1]
                        video_title = os.path.splitext(expected_final_filename)[0] # 拡張子なしのタイトル
                        expected_final_filename = f"{video_title}{actual_extension}"


                if downloaded_file_path and os.path.exists(downloaded_file_path):
                    st.success(f"✅ 「{os.path.basename(expected_final_filename)}」のダウンロードが完了しました！")

                    with open(downloaded_file_path, "rb") as file_to_download:
                        st.download_button(
                            label="ファイルをダウンロード",
                            data=file_to_download,
                            file_name=expected_final_filename, # ユーザーに提示するファイル名
                            mime=f"application/octet-stream" # 一般的なバイナリファイルタイプ
                        )
                else:
                    st.error("❌ ダウンロードされたファイルが見つかりませんでした。")

        except Exception as e:
            st.error(f"❌ エラーが発生しました: {str(e)}")
            st.exception(e) # 詳細なエラー情報を表示 (デバッグ用)

st.markdown("---")
st.markdown("ご利用上の注意: ダウンロードしたコンテンツの著作権にご注意ください。個人利用の範囲に留めてください。")

if st.button("ログアウト"):
    st.logout()


