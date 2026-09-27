from __future__ import annotations
import hmac
import streamlit as st

from database import (
    add_message, delete_message, list_messages, reset_layout, update_message
)
from renderer import (
    W, H, MIN_FONT_PT, compute_layout, find_overlaps, make_a3_pdf,
    png_bytes, preview_bytes, render_pages
)

st.set_page_config(page_title="스윙피버 69기 롤링페이퍼", page_icon="🍂", layout="wide")

st.markdown("""
<style>
.block-container {max-width: 1180px; padding-top: 1.6rem;}
.hero {padding: 1.3rem 1.4rem; border-radius: 20px; background: #fff4dd; border: 1px solid #ead6ac;}
.small {color:#7a685d; font-size:.92rem;}
</style>
""", unsafe_allow_html=True)


def secret_eq(a: str, b: str) -> bool:
    return hmac.compare_digest((a or "").encode(), (b or "").encode())


def participant_authorized() -> bool:
    expected = st.secrets.get("PARTICIPANT_CODE", "")
    invite = st.query_params.get("invite", "")
    if expected and invite and secret_eq(str(invite), str(expected)):
        return True
    if st.session_state.get("participant_ok"):
        return True
    return False


def admin_authorized() -> bool:
    return bool(st.session_state.get("admin_ok"))


def login_participant() -> None:
    st.markdown('<div class="hero"><h2>🍁 린디합 69기 롤링페이퍼</h2><p>초대받은 분만 메시지를 남길 수 있어요.</p></div>', unsafe_allow_html=True)
    with st.form("participant_login"):
        code = st.text_input("참여 코드", type="password", placeholder="전달받은 참여 코드를 입력하세요")
        ok = st.form_submit_button("입장하기", use_container_width=True)
        if ok:
            if secret_eq(code, st.secrets.get("PARTICIPANT_CODE", "")):
                st.session_state.participant_ok = True
                st.rerun()
            st.error("참여 코드가 맞지 않습니다.")


def participant_page() -> None:
    st.markdown('<div class="hero"><h2>🍂 To. 서호싸부</h2><p>스윙피버 린디합 초중급 69기 롤링페이퍼에 한마디 남겨주세요.</p></div>', unsafe_allow_html=True)
    messages = list_messages()
    st.progress(min(len(messages) / 40, 1.0), text=f"현재 {len(messages)}명 참여 · 목표 40명")

    st.info("인쇄했을 때 글씨가 작아지지 않도록 **50~80자 정도를 권장**하고, 최대 110자로 제한합니다.")
    with st.form("write_message", clear_on_submit=True):
        c1, c2 = st.columns([2, 1])
        nickname = c1.text_input("닉네임", max_chars=20, placeholder="예: 쨀")
        icon = c2.selectbox("표시", ["♥", "♪", "★", "♬", "✦"])
        message = st.text_area("메시지", max_chars=110, height=170, placeholder="서호싸부에게 전하고 싶은 말을 적어주세요 :) ")
        submitted = st.form_submit_button("메시지 남기기", type="primary", use_container_width=True)
        if submitted:
            if not nickname.strip():
                st.error("닉네임을 입력해주세요.")
            elif not message.strip():
                st.error("메시지를 입력해주세요.")
            else:
                add_message(nickname, message, icon)
                st.success("메시지가 등록되었습니다! 🍁")
                st.balloons()
                st.rerun()

    st.caption("작성된 메시지 내용은 선물의 재미를 위해 참여자 화면에는 공개하지 않습니다. 최종 배치는 관리자만 확인·수정합니다.")


def admin_login() -> None:
    with st.form("admin_login"):
        pw = st.text_input("관리자 비밀번호", type="password")
        if st.form_submit_button("관리자 로그인", use_container_width=True):
            if secret_eq(pw, st.secrets.get("ADMIN_PASSWORD", "")):
                st.session_state.admin_ok = True
                st.rerun()
            st.error("비밀번호가 맞지 않습니다.")


def msg_label(m: dict) -> str:
    body = (m.get("message") or "").replace("\n", " ")
    return f"{m.get('nickname','')} · {body[:28]}{'…' if len(body)>28 else ''}"


def admin_page() -> None:
    st.title("🛠️ 관리자 편집실")
    messages = list_messages(include_hidden=True)
    visible = [m for m in messages if not m.get("is_hidden")]
    st.write(f"총 등록 **{len(messages)}개** · 최종 포함 **{len(visible)}개**")

    front, back, layout = render_pages(messages)
    overlaps = find_overlaps(layout)
    overflow = [m for p in layout.values() for m in p if m.get("_overflow")]

    m1, m2, m3 = st.columns(3)
    m1.metric("포함 메시지", len(visible))
    m2.metric("겹침 감지", len(overlaps))
    m3.metric("공간 초과", len(overflow))
    if overlaps:
        st.warning("현재 서로 겹치는 메시지가 있습니다. 아래 ‘위치 조정’에서 X/Y/폭을 수정해주세요.")
    if overflow:
        st.warning("아래쪽 인쇄영역을 벗어나는 메시지가 있습니다. 긴 문구를 줄이거나 앞/뒤 페이지를 조정해주세요.")

    tab_preview, tab_edit, tab_download = st.tabs(["A3 미리보기", "메시지·위치 조정", "최종 다운로드"])

    with tab_preview:
        c1, c2 = st.columns(2)
        c1.subheader("앞면")
        c1.image(preview_bytes(front), use_container_width=True)
        c2.subheader("뒷면")
        c2.image(preview_bytes(back), use_container_width=True)
        st.caption("빨간 테두리가 보이면 해당 메시지가 현재 영역을 넘어간 상태입니다. 최종 출력은 A3 300dpi로 생성됩니다.")

    with tab_edit:
        if not messages:
            st.info("아직 등록된 메시지가 없습니다.")
        else:
            options = {m["id"]: msg_label(m) for m in messages}
            selected_id = st.selectbox("수정할 메시지", list(options), format_func=lambda x: options[x])
            m = next(x for x in messages if x["id"] == selected_id)

            st.markdown("#### 1) 내용 수정")
            with st.form("edit_content"):
                nickname = st.text_input("닉네임", value=m.get("nickname", ""), max_chars=20)
                icon = st.selectbox("표시", ["♥", "♪", "★", "♬", "✦"], index=["♥", "♪", "★", "♬", "✦"].index(m.get("icon")) if m.get("icon") in ["♥", "♪", "★", "♬", "✦"] else 0)
                text = st.text_area("문구", value=m.get("message", ""), max_chars=110, height=160)
                hidden = st.checkbox("최종본에서 숨기기", value=bool(m.get("is_hidden")))
                if st.form_submit_button("내용 저장", type="primary"):
                    update_message(selected_id, nickname=nickname.strip(), message=text.strip(), icon=icon, is_hidden=hidden)
                    st.success("저장했습니다.")
                    st.rerun()

            st.markdown("#### 2) 위치 조정 — 관리자 전용")
            st.caption("기본은 자동배치입니다. 위치를 직접 지정하면 해당 메시지만 수동배치로 전환됩니다.")

            # Derive current position from computed layout when still automatic.
            found = None
            for pno, arr in layout.items():
                for item in arr:
                    if item["id"] == selected_id:
                        found = (pno, item)
                        break
            if found:
                auto_page, item = found
                rx, ry, rw, rh = item["_rect"]
            else:
                auto_page, rx, ry, rw, rh = 2, 150, 1200, 1000, 500

            current_page = int(m.get("page") or auto_page)
            current_x = int(m.get("x") if m.get("x") is not None else rx)
            current_y = int(m.get("y") if m.get("y") is not None else ry)
            current_w = int(m.get("w") if m.get("w") is not None else rw)
            current_font = float(m.get("font_pt") or item.get("_auto_font_pt", 17.0) if found else 17.0)

            with st.form("position_form"):
                page = st.radio("페이지", [1, 2], horizontal=True, index=0 if current_page == 1 else 1, format_func=lambda p: "앞면" if p == 1 else "뒷면")
                x_pct = st.slider("가로 위치 X (%)", 0.0, 90.0, min(90.0, current_x / W * 100), 0.5)
                y_pct = st.slider("세로 위치 Y (%)", 0.0, 92.0, min(92.0, current_y / H * 100), 0.5)
                w_pct = st.slider("카드 폭 (%)", 18.0, 48.0, min(48.0, max(18.0, current_w / W * 100)), 0.5)
                font_pt = st.slider("본문 글씨 크기 (pt)", float(MIN_FONT_PT), 22.0, min(22.0, max(float(MIN_FONT_PT), current_font)), 0.5)
                if st.form_submit_button("이 위치로 저장", type="primary"):
                    update_message(
                        selected_id,
                        page=int(page),
                        x=int(x_pct / 100 * W),
                        y=int(y_pct / 100 * H),
                        w=int(w_pct / 100 * W),
                        h=None,
                        font_pt=float(font_pt),
                    )
                    st.success("위치를 저장했습니다. 미리보기에서 겹침 여부를 확인하세요.")
                    st.rerun()

            b1, b2 = st.columns(2)
            if b1.button("이 메시지만 자동배치로 되돌리기", use_container_width=True):
                update_message(selected_id, page=None, x=None, y=None, w=None, h=None, font_pt=None)
                st.rerun()
            if b2.button("모든 메시지 자동 재배치", use_container_width=True):
                reset_layout()
                st.rerun()

            st.markdown("#### 3) 삭제")
            confirm = st.checkbox("선택한 메시지를 영구 삭제하겠습니다.")
            if st.button("선택 메시지 삭제", type="secondary", disabled=not confirm):
                delete_message(selected_id)
                st.success("삭제했습니다.")
                st.rerun()

    with tab_download:
        pdf = make_a3_pdf(front, back)
        st.download_button("📄 A3 양면 PDF 다운로드", pdf, file_name="swingfever_69_rollingpaper_A3.pdf", mime="application/pdf", type="primary", use_container_width=True)
        c1, c2 = st.columns(2)
        c1.download_button("앞면 PNG (300dpi)", png_bytes(front), file_name="rollingpaper_front_A3.png", mime="image/png", use_container_width=True)
        c2.download_button("뒷면 PNG (300dpi)", png_bytes(back), file_name="rollingpaper_back_A3.png", mime="image/png", use_container_width=True)
        st.info("인쇄소에는 PDF를 전달하고 ‘A3, 실제 크기 100%, 양면, 긴 변 기준 뒤집기 여부 확인’으로 요청하는 것을 권장합니다.")

    if st.button("관리자 로그아웃"):
        st.session_state.admin_ok = False
        st.rerun()


mode = st.query_params.get("mode", "write")
if mode == "admin":
    if admin_authorized():
        admin_page()
    else:
        st.title("관리자 로그인")
        admin_login()
else:
    if participant_authorized():
        participant_page()
    else:
        login_participant()

st.divider()
st.markdown('<p class="small">관리자 주소: 현재 주소 뒤에 <code>?mode=admin</code> 을 붙여 접속하세요.</p>', unsafe_allow_html=True)
