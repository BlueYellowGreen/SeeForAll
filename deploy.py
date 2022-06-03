import streamlit as st
from bokeh.models import CustomJS
from bokeh.models.widgets import Button
from streamlit_bokeh_events import streamlit_bokeh_events

import numpy as np
from gtts import gTTS

from PIL import Image
from io import BytesIO
import requests
import base64


# Clear session
def file_upload_on_change():
    if 'query' in st.session_state:
        st.session_state.query = ''
    if 'vqa_input_type' in st.session_state:
        st.session_state.input_type = 'Mic'
    if 'vqa_list' in st.session_state:
        st.session_state.vqa_list = []


st.set_page_config(
    page_title='리트리버',
    page_icon='🐕',
    layout='wide',
)

st.title('🐕 리트리버')

st.text('')
st.text('눈이 불편하신 분들을 도와주는 안내견 🐕 리트리버 입니다!')

st.text('')
st.text('')
st.text('')

URL = st.secrets["url"]
ping = requests.get(f'{URL}/api/v1/ping').status_code

if ping == 200:
    uploaded_file = st.file_uploader('이미지를 올려주세요', on_change=file_upload_on_change)

    bcol1, _, bcol3 = st.columns([10, 1, 10])
    if uploaded_file is not None:
        img = Image.open(uploaded_file)
        img_np = np.array(img)
        img_np = np.fliplr(np.swapaxes(img_np, 0, 1))
        bcol1.image(img_np)

        # IC POST + process
        ic_res = requests.post(
            url=f'{URL}/api/v1/ic',
            data={'beam': 3},
            files={'file': uploaded_file.getvalue()}
        )

        try:
            caption = ic_res.json()['caption']
            device = ic_res.json()['device']
            time_str = ic_res.json()['inference_time'][:5]
            bcol3.markdown(f"#### {caption}")
            bcol3.caption(f"{device} time {time_str}s")
        except:
            caption = "무슨 사진인지 잘 모르겠습니다 😥"
            bcol3.markdown(f"무슨 사진인지 잘 모르겠습니다 😥")
        bcol3.text('')
        bcol3.text('')
        

        # IC Caption TTS
        caption_tts = gTTS(text=caption, lang='ko')
        mp3_fp = BytesIO()
        caption_tts.write_to_fp(mp3_fp)
        audio_source = "data:audio/ogg;base64,%s"%base64.b64encode(mp3_fp.getvalue()).decode()
        audio_html = """
            <audio controls autoplay>
            <source src="%s" type="audio/ogg">
            해당 브라우저에서 지원하지 않는 오디오 플레이어입니다.
            </audio>
            """%audio_source
        bcol3.markdown(audio_html, unsafe_allow_html=True)


        bcol3.text('')
        bcol3.selectbox(
            '입력 타입을 선택해주세요. (마이크는 크롬 브라우저에서만 동작합니다)',
            ('Mic', 'Keyboard'),
            key='vqa_input_type'
        )

        # STT Mic Input
        if st.session_state.vqa_input_type == 'Mic':
            with bcol3.container():
                # MIC setting
                stt_button = Button(label="마이크 입력", width=20)
                stt_button.js_on_event("button_click", CustomJS(code="""
                    var recognition = new webkitSpeechRecognition();
                    recognition.continuous = false;
                    recognition.interimResults = true;
                    recognition.lang = "ko-KR";
                    recognition.maxAlternatives = 100;

                    recognition.onresult = function (e) {
                        var value = "";
                        for (var i = e.resultIndex; i < e.results.length; ++i) {
                            if (e.results[i].isFinal) {
                                value += e.results[i][0].transcript;
                            }
                        }
                        if ( value != "") {
                            document.dispatchEvent(new CustomEvent("GET_TEXT", {detail: value}));
                        }
                    }
                    recognition.start();
                    """))

                result = streamlit_bokeh_events(
                    stt_button,
                    events="GET_TEXT",
                    key="listen",
                    refresh_on_update=False,
                    override_height=45,
                    debounce_time=0)
        
                if result:
                    if "GET_TEXT" in result:
                        st.session_state.query = result.get("GET_TEXT")
                        if st.session_state.query and st.session_state.query[-1] != '?':
                            st.session_state.query += '?'
        # Keyboard Input
        else:
            st.session_state.query = bcol3.text_input('질문을 적으시고 Enter 를 눌러주세요.', key='vqa_keyboard_input')

        if 'query' in st.session_state and st.session_state.query:
            audio_space = bcol3.empty()
            # VQA POST + process
            with bcol3.container():
                with st.spinner('대답 준비 중입니다...'):
                    vqa_res = requests.post(
                        url=f'{URL}/api/v1/vqa',
                        data={'query': ' '+st.session_state.query},
                        files={'file': uploaded_file.getvalue()})

                    Q = f"[질문]: {st.session_state.query}"
                    st.session_state.answer = vqa_res.json()['answer']
                    if st.session_state.answer == 'Yes':
                        st.session_state.answer = '네'
                    elif st.session_state.answer == 'no':
                        st.session_state.answer = '아니오'
                    # A = f"[대답]: {vqa_res.json()['answer']}"
                    A = f"[대답]: {st.session_state.answer}"
                    C = f"{vqa_res.json()['device']} time {vqa_res.json()['inference_time'][:5]}s"

                    if 'vqa_list' in st.session_state:
                        st.session_state.vqa_list = [(Q, A, C)] + st.session_state.vqa_list
                    else:
                        st.session_state.vqa_list = [(Q, A, C)]
                    st.session_state.query = ''

                    # VQA Answer TTS Process
                    audio_space.empty()
                    answer_tts = gTTS(text=st.session_state.answer, lang='ko')
                    mp3_fp_2 = BytesIO()
                    answer_tts.write_to_fp(mp3_fp_2)
                    audio_sourc_2 = "data:audio/ogg;base64,%s"%base64.b64encode(mp3_fp_2.getvalue()).decode()
                    audio_html_2 = """
                        <audio controls autoplay currentTime=0>
                        <source src="%s" type="audio/ogg">
                        해당 브라우저에서 지원하지 않는 오디오 플레이어입니다.
                        </audio>
                        """%audio_sourc_2

                    # VQA Answer TTS
                    audio_space.markdown(audio_html_2, unsafe_allow_html=True)

        if 'vqa_list' in st.session_state and len(st.session_state.vqa_list) != 0:
            for q, a, c in st.session_state.vqa_list:
                bcol3.text(q)
                bcol3.text(a)
                bcol3.caption(c)
else:
    st.error('Sorry, Server is not online.')
