import requests
import os
import json
import streamlit as st
from dotenv import load_dotenv

# .envファイルからAPIキーを読み込む
load_dotenv()
API_KEY = os.getenv("TMDB_API_KEY")
BASE_URL = "https://api.themoviedb.org/3"
POSTER_BASE_URL = "https://image.tmdb.org/t/p/w300"
FAVORITES_FILE = "favorites.json"


# ─────────────────────────────────────
# API通信
# ─────────────────────────────────────

def get_genres():
    """ジャンル一覧を取得する"""
    url = f"{BASE_URL}/genre/movie/list"
    res = requests.get(url, params={"api_key": API_KEY, "language": "ja"})
    res.raise_for_status()
    return res.json()["genres"]


def discover_movies(genre_id, min_rating=7.0, year=None, page=1):
    """条件に合う映画一覧を取得する"""
    params = {
        "api_key": API_KEY,
        "language": "ja",
        "with_genres": genre_id,
        "vote_average.gte": min_rating,
        "sort_by": "popularity.desc",
        "page": page,
    }
    if year:
        params["primary_release_year"] = year

    url = f"{BASE_URL}/discover/movie"
    res = requests.get(url, params=params)
    res.raise_for_status()
    return res.json()["results"]


def get_cast(movie_id):
    """映画のキャスト情報を取得する"""
    url = f"{BASE_URL}/movie/{movie_id}/credits"
    res = requests.get(url, params={"api_key": API_KEY, "language": "ja"})
    res.raise_for_status()
    cast = res.json().get("cast", [])
    return cast[:5]  # 上位5人だけ返す


# ─────────────────────────────────────
# お気に入り管理
# ─────────────────────────────────────

def load_favorites():
    """お気に入りをファイルから読み込む"""
    if os.path.exists(FAVORITES_FILE):
        with open(FAVORITES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_favorites(favorites):
    """お気に入りをファイルに保存する"""
    with open(FAVORITES_FILE, "w", encoding="utf-8") as f:
        json.dump(favorites, f, ensure_ascii=False, indent=2)


def add_favorite(movie):
    """お気に入りに追加する"""
    favorites = load_favorites()
    if not any(f["id"] == movie["id"] for f in favorites):
        favorites.append({"id": movie["id"], "title": movie.get("title"), "poster_path": movie.get("poster_path"), "vote_average": movie.get("vote_average"), "release_date": movie.get("release_date", "")})
        save_favorites(favorites)


def remove_favorite(movie_id):
    """お気に入りから削除する"""
    favorites = load_favorites()
    favorites = [f for f in favorites if f["id"] != movie_id]
    save_favorites(favorites)


def is_favorite(movie_id):
    """お気に入り済みかどうか確認する"""
    favorites = load_favorites()
    return any(f["id"] == movie_id for f in favorites)


# ─────────────────────────────────────
# 映画カードの表示
# ─────────────────────────────────────

def show_movie_card(movie):
    """映画1件分のカードを表示する"""
    movie_id = movie["id"]
    title = movie.get("title", "タイトル不明")
    year_str = movie.get("release_date", "")[:4] or "不明"
    rating = movie.get("vote_average", "N/A")
    overview = movie.get("overview") or "あらすじなし"
    poster_path = movie.get("poster_path")

    if poster_path:
        st.image(POSTER_BASE_URL + poster_path, width=150)

    st.markdown(f"**{title}** ({year_str})")
    st.markdown(f"⭐ {rating}")
    st.write(overview[:120] + "..." if len(overview) > 120 else overview)

    # キャスト表示
    with st.expander("キャストを見る"):
        cast = get_cast(movie_id)
        if cast:
            for actor in cast:
                st.write(f"・{actor.get('name', '不明')} / {actor.get('character', '不明')}")
        else:
            st.write("キャスト情報がありません。")

    # お気に入りボタン
    if is_favorite(movie_id):
        if st.button("❤️ お気に入り解除", key=f"fav_{movie_id}"):
            remove_favorite(movie_id)
            st.rerun()
    else:
        if st.button("🤍 お気に入り追加", key=f"fav_{movie_id}"):
            add_favorite(movie)
            st.rerun()

    st.divider()


# ─────────────────────────────────────
# Streamlit UI
# ─────────────────────────────────────

st.title("🎬 映画レコメンダー")

if not API_KEY:
    st.error("エラー: .envファイルにTMDB_API_KEYが設定されていません。")
    st.stop()

# タブで「検索」と「お気に入り」を切り替え
tab1, tab2 = st.tabs(["🔍 映画を探す", "❤️ お気に入り"])


# ─── タブ1: 映画検索 ───
with tab1:
    # サイドバーに検索条件を配置
    st.sidebar.header("🔍 検索条件")
    genres = get_genres()
    genre_names = [g["name"] for g in genres]
    genre_map = {g["name"]: g["id"] for g in genres}

    selected_genre_name = st.sidebar.selectbox("ジャンル", genre_names)
    min_rating = st.sidebar.slider("最低評価スコア", 0.0, 10.0, 7.0, 0.5)
    year = st.sidebar.text_input("公開年（例: 2023 / 空欄でも可）")
    search_button = st.sidebar.button("検索する")

    # ページ数をセッションで管理
    if "page" not in st.session_state:
        st.session_state.page = 1
    if "movies" not in st.session_state:
        st.session_state.movies = []

    # 検索実行
    if search_button:
        st.session_state.page = 1
        genre_id = genre_map[selected_genre_name]
        year_value = int(year) if year.isdigit() else None
        with st.spinner("検索中..."):
            st.session_state.movies = discover_movies(genre_id, min_rating, year_value, page=1)
        st.session_state.genre_id = genre_id
        st.session_state.min_rating = min_rating
        st.session_state.year_value = year_value

    # 映画一覧表示
    if st.session_state.movies:
        st.subheader(f"{selected_genre_name} のおすすめ映画")
        cols = st.columns(2)
        for i, movie in enumerate(st.session_state.movies):
            with cols[i % 2]:
                show_movie_card(movie)

        # もっと見るボタン
        if st.button("▼ もっと見る"):
            st.session_state.page += 1
            with st.spinner("読み込み中..."):
                more_movies = discover_movies(
                    st.session_state.genre_id,
                    st.session_state.min_rating,
                    st.session_state.year_value,
                    page=st.session_state.page
                )
            st.session_state.movies += more_movies
            st.rerun()


# ─── タブ2: お気に入り ───
with tab2:
    favorites = load_favorites()
    if not favorites:
        st.info("まだお気に入りがありません。映画を探してお気に入り追加してみましょう！")
    else:
        st.subheader(f"お気に入り ({len(favorites)}件)")
        cols = st.columns(2)
        for i, movie in enumerate(favorites):
            with cols[i % 2]:
                poster_path = movie.get("poster_path")
                if poster_path:
                    st.image(POSTER_BASE_URL + poster_path, width=150)
                year_str = movie.get("release_date", "")[:4] or "不明"
                st.markdown(f"**{movie['title']}** ({year_str})")
                st.markdown(f"⭐ {movie.get('vote_average', 'N/A')}")
                if st.button("❤️ お気に入り解除", key=f"remove_{movie['id']}"):
                    remove_favorite(movie["id"])
                    st.rerun()
                st.divider()