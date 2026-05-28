import streamlit as st
import requests
import plotly.graph_objects as go
import pandas as pd
import google.generativeai as genai
import json
import re

st.set_page_config(page_title="CS2 Market Sentiment Index", layout="centered")

def extract_reddit_data(keyword, time_filter="all", limit=100):
    search_url = f"https://www.reddit.com/r/csgomarketforum/search.json"
    search_params = {
        "q": keyword,
        "restrict_sr": "on",
        "sort": "relevance",
        "t": time_filter,
        "limit": 5
    }
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    extracted_data = []
    import time
    try:
        response = requests.get(search_url, params=search_params, headers=headers)
        if response.status_code == 200:
            posts = response.json().get('data', {}).get('children', [])
            post = response.json().get('data', {})
            
            for post in posts:
                post_data = post.get('data', {})
                permalink = post_data.get('permalink', '')
                post_title = post_data.get('title', '')
                
                if not permalink:
                    continue
                    
                post_url = f"https://www.reddit.com{permalink[:-1]}.json"
                try:
                    post_response = requests.get(post_url, headers=headers)
                    if post_response.status_code == 200:
                        post_json = post_response.json()
                        if isinstance(post_json, list) and len(post_json) > 1:
                            comments = post_json[1].get('data', {}).get('children', [])
                            for comment in comments:
                                if comment.get('kind') == 't1':
                                    c_data = comment.get('data', {})
                                    body = c_data.get('body', '')
                                    if body and body not in ['[deleted]', '[removed]']:
                                        extracted_data.append({
                                            "title": f"Re: {post_title[:40]}...",
                                            "text": body,
                                            "url": f"https://www.reddit.com{c_data.get('permalink', permalink)}",
                                            "score": c_data.get('score', 0)
                                        })
                    time.sleep(0.5)
                except Exception as inner_e:
                    pass
                    
                if len(extracted_data) >= limit:
                    break
        else:
            st.warning(f"Reddit bloqueó temporalmente la IP ({response.status_code}). Intenta de nuevo en unos minutos.")
    except Exception as e:
        st.error(f"Error al conectar con Reddit: {e}")
        
    return extracted_data[:limit]

def analyze_sentiment(data, api_key):
    results = []
    summary = {"Bullish_pct": 0, "Bearish_pct": 0, "Neutral_pct": 0, "Total": 0}
    
    if not data:
        return results, summary
        
    try:
        genai.configure(api_key=api_key)
        chosen_model = None
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                if 'flash' in m.name or 'pro' in m.name:
                    chosen_model = m.name
                    break
        if not chosen_model:
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    chosen_model = m.name
                    break
                    
        if not chosen_model:
            st.error("Tu clave de API no tiene acceso a ningún modelo.")
            return results, summary
            
        model = genai.GenerativeModel(chosen_model)
        
        comments_text = ""
        for i, item in enumerate(data):
            text = f"{item['title']}. {item['text']}"[:300]
            if len(text.strip()) > 5:
                comments_text += f"ID: {i} | Texto: {text}\n"
                
        if not comments_text:
            return results, summary
            
        prompt = f"""
        Actúa como un experto financiero en el mercado de skins de Counter-Strike 2.
        Evalúa si cada comentario de esta lista es Bullish (Alcista/Comprar), Bearish (Bajista/Vender) o Neutral.
        Entiende la jerga: "HODL", "to the moon" es Bullish. "Crash", "dump", "sell" es Bearish.
        
        Devuelve SOLO un array JSON válido con este formato exacto:
        [
          {{"id": 0, "sentiment": "Bullish", "confidence": 95}}
        ]
        
        Comentarios:
        {comments_text}
        """
        
        response = model.generate_content(prompt)
        
        match = re.search(r'\[.*\]', response.text, re.DOTALL)
        if match:
            predictions = json.loads(match.group(0))
        else:
            predictions = json.loads(response.text)
            
        counts = {"Bullish": 0, "Bearish": 0, "Neutral": 0}
        
        for pred in predictions:
            idx = pred.get("id")
            sentiment = pred.get("sentiment", "Neutral")
            if sentiment not in counts:
                sentiment = "Neutral"
            confidence = pred.get("confidence", 50)
            
            if idx is not None and 0 <= idx < len(data):
                item = data[idx]
                counts[sentiment] += 1
                market_label = sentiment
                
                results.append({
                    "Post (Título)": item['title'],
                    "Sentimiento": market_label,
                    "Confianza": f"{confidence}%",
                    "Upvotes": item['score'],
                    "URL": item['url']
                })
                
        total_valid = sum(counts.values())
        if total_valid > 0:
            summary = {
                "Bullish_pct": (counts["Bullish"] / total_valid) * 100,
                "Bearish_pct": (counts["Bearish"] / total_valid) * 100,
                "Neutral_pct": (counts["Neutral"] / total_valid) * 100,
                "Total": total_valid
            }
            
    except Exception as e:
        st.error(f"Error procesando el JSON de Gemini: {e}")
        
    return results, summary

def generate_gemini_summary(data, api_key, keyword):
    try:
        genai.configure(api_key=api_key)
        
        chosen_model = None
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                if 'flash' in m.name or 'pro' in m.name:
                    chosen_model = m.name
                    break
        
        if not chosen_model:
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    chosen_model = m.name
                    break
                    
        if not chosen_model:
            return "Error: Tu clave de API no tiene acceso a ningún modelo de generación de texto."
            
        model = genai.GenerativeModel(chosen_model)
        
        valid_comments = [item['text'] for item in data if len(item['text'].strip()) > 10]
        text_to_summarize = "\n---\n".join(valid_comments[:30])
        
        if not text_to_summarize:
            return None
            
        prompt = f"""
        Eres un analista experto en el mercado de skins e items de Counter-Strike 2.
        A continuación te proporciono una serie de comentarios recientes extraídos de Reddit 
        sobre la palabra clave '{keyword}'.
        
        Por favor, redacta un resumen analítico de un párrafo en español indicando:
        1. Cuál es el sentimiento general (positivo, negativo, incierto).
        2. Los puntos principales o motivos que la comunidad menciona.
        
        Comentarios de la comunidad:
        {text_to_summarize}
        """
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"Error al generar resumen con Gemini: {e}")
        return None

def plot_sentiment_gauge(bullish_pct):
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = bullish_pct,
        number = {"suffix": "%", "font": {"color": "#E6E9EF"}},
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "Índice de Sentimiento (Bullish)", 'font': {'size': 24, 'color': "#E4A11B"}},
        gauge = {
            'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "white"},
            'bar': {'color': "rgba(0,0,0,0)"},
            'bgcolor': "rgba(0,0,0,0)",
            'borderwidth': 2,
            'bordercolor': "#1C2026",
            'steps': [
                {'range': [0, 40], 'color': "#ff4b4b"},
                {'range': [40, 60], 'color': "#faca2b"},
                {'range': [60, 100], 'color': "#00cc96"}
            ],
            'threshold': {
                'line': {'color': "white", 'width': 5},
                'thickness': 0.75,
                'value': bullish_pct
            }
        }
    ))
    
    fig.update_layout(
        height=350, 
        margin=dict(l=10, r=10, t=50, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#E6E9EF")
    )
    return fig

def main():
    st.title("CS2 Market Sentiment Index")
    st.markdown("Analiza el sentimiento del mercado de **Counter-Strike 2** usando discusiones de Reddit y procesamiento de lenguaje natural (NLP) financiero.")
    
    gemini_api_key = st.secrets.get("GEMINI_API_KEY", "")
    if not gemini_api_key or gemini_api_key == "TU_GEMINI_API_KEY_AQUI":
        st.warning("Debes configurar tu GEMINI_API_KEY en el archivo `.streamlit/secrets.toml` para usar la aplicación.")
        st.stop()
        
    st.write("---")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        keyword = st.text_input("Palabra clave a analizar:", placeholder="Ej. Kilowatt Case, Paris 2023, Doppler...")
    with col2:
        time_options = {
            "Última semana": "week",
            "Último mes": "month",
            "Último año": "year",
            "Todo el tiempo": "all"
        }
        selected_time_label = st.selectbox("Filtro de Tiempo:", list(time_options.keys()), index=1)
        time_filter = time_options[selected_time_label]
        
    with col3:
        st.write("")
        st.write("")
        analyze_btn = st.button("Analizar Mercado", use_container_width=True)
        
    if analyze_btn:
        if not keyword.strip():
            st.warning("Por favor, introduce un término de búsqueda válido.")
            return
            
        with st.spinner(f"Buscando los últimos posts sobre '{keyword}' en r/csgomarketforum..."):
            reddit_data = extract_reddit_data(keyword, time_filter=time_filter, limit=150)
            
        if not reddit_data:
            st.error("No se encontró información o hubo un error de red.")
            return
            
        with st.spinner(f"Evaluando {len(reddit_data)} posts con la IA de Google Gemini..."):
            detailed_results, summary = analyze_sentiment(reddit_data, gemini_api_key)
            
        if summary["Total"] == 0:
            st.info("No hay suficiente texto útil en los posts encontrados para realizar el análisis.")
            return
            
        st.session_state['analysis_data'] = {
            'detailed_results': detailed_results,
            'summary': summary,
            'reddit_data': reddit_data,
            'keyword': keyword,
            'time_filter': time_filter
        }

    if 'analysis_data' in st.session_state:
        data = st.session_state['analysis_data']
        detailed_results = data['detailed_results']
        summary = data['summary']
        reddit_data = data['reddit_data']
        kw = data['keyword']
        
        st.write("---")
        st.subheader("Resultados del Análisis")
        st.markdown(f"Se analizaron con éxito **{summary['Total']}** comentarios relevantes sobre **{kw}**.")
        
        state_kw = st.session_state.get('last_kw')
        state_tf = st.session_state.get('last_tf')
        
        if 'gemini_summary' not in st.session_state or state_kw != kw or state_tf != data.get('time_filter'):
            with st.spinner("Generando resumen cualitativo de la comunidad con IA (Gemini)..."):
                summary_text = generate_gemini_summary(reddit_data, gemini_api_key, kw)
                st.session_state['gemini_summary'] = summary_text
                st.session_state['last_kw'] = kw
                st.session_state['last_tf'] = data.get('time_filter')
        
        if st.session_state.get('gemini_summary'):
            st.info(f"**Resumen de la Comunidad:**\n\n{st.session_state['gemini_summary']}")
        
        st.write("---")
        bullish_val = summary['Bullish_pct']
        sentiment_text = "Alcista (Bullish)" if bullish_val >= 60 else "Bajista (Bearish)" if bullish_val <= 40 else "Neutral"
        st.markdown(f"### Veredicto del Mercado: **{sentiment_text}**")
        
        fig = plot_sentiment_gauge(bullish_val)
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("#### Desglose de Sentimiento")
        c1, c2, c3 = st.columns(3)
        c1.metric(label="Alcistas (Bullish)", value=f"{summary['Bullish_pct']:.1f}%")
        c2.metric(label="Neutrales", value=f"{summary['Neutral_pct']:.1f}%")
        c3.metric(label="Bajistas (Bearish)", value=f"{summary['Bearish_pct']:.1f}%")
        
        st.write("---")
        st.subheader("Lista de Comentarios Analizados")
        df_results = pd.DataFrame(detailed_results)
        
        df_results = df_results.sort_values(by="Upvotes", ascending=False)
        
        rows_per_page = 10
        total_pages = max(1, (len(df_results) - 1) // rows_per_page + 1)
        
        if total_pages > 1:
            page_number = st.number_input(f"Página (1 de {total_pages})", min_value=1, max_value=total_pages, step=1)
        else:
            page_number = 1
            
        start_idx = (page_number - 1) * rows_per_page
        end_idx = start_idx + rows_per_page
        
        st.dataframe(
            df_results.iloc[start_idx:end_idx][["Post (Título)", "Sentimiento", "Confianza", "Upvotes", "URL"]], 
            use_container_width=True,
            hide_index=True,
            column_config={
                "URL": st.column_config.LinkColumn(
                    "Enlace al Post",
                    display_text="Ver en Reddit"
                ),
                "Upvotes": st.column_config.NumberColumn(
                    "Upvotes",
                    format="%d"
                )
            }
        )

if __name__ == "__main__":
    main()
