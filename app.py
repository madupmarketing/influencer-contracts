import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import date, datetime

BASE = Path(__file__).parent
TEMPLATE = BASE / "template" / "표준계약서_원본.docx"

st.set_page_config(
    page_title="인플루언서 계약서 자동화",
    page_icon=":material/contract:",
    layout="wide",
)

st.markdown("""
<style>
.block-container { padding-top: 1.5rem; }
.section-title {
    font-size: 0.72rem; font-weight: 700; letter-spacing: .08em;
    text-transform: uppercase; opacity: 0.55; margin-bottom: .4rem;
}
</style>
""", unsafe_allow_html=True)

# 세션 상태: 생성 내역 목록
if "history" not in st.session_state:
    st.session_state.history = []  # [{name, filename, created_at, doc_bytes}]

st.markdown("## :material/contract: 인플루언서 계약서 자동화")
st.caption("매드업 표준 계약서 기반 · 인플루언서 정보 입력 → 계약서 초안 자동 생성")
st.divider()

tab_new, tab_list = st.tabs([":material/add: 새 계약서 작성", ":material/folder_open: 생성 내역"])

# ════════════════════════════════════════════════════════
# TAB 1: 새 계약서 작성
# ════════════════════════════════════════════════════════
with tab_new:
    st.markdown('<p class="section-title">인플루언서 정보</p>', unsafe_allow_html=True)

    col_a, col_b = st.columns(2, gap="large")

    with col_a:
        with st.container(border=True):
            st.markdown("**기본 정보**")
            계약자유형 = st.radio("계약자 유형 *", ["개인", "사업자"], horizontal=True)
            if 계약자유형 == "개인":
                수임인 = st.text_input("이름 *", placeholder="홍길동")
            else:
                수임인 = st.text_input("사업자명 *", placeholder="주식회사 OO")
            이메일 = st.text_input("이메일 (발송용)", placeholder="influencer@gmail.com")
            캠페인명 = st.text_input("캠페인명 *", placeholder="2026 여름 뷰티 캠페인")
            주제 = st.text_input("콘텐츠 주제", placeholder="여름 스킨케어 솔직 리뷰")

        with st.container(border=True):
            st.markdown("**채널 정보**")
            채널명 = st.text_input("채널명", placeholder="홍길동TV")
            채널URL = st.text_input("채널 URL", placeholder="https://www.youtube.com/@abc")
            유튜브링크 = st.text_input("유튜브 링크 (동일하거나 특정 영상)", placeholder="https://www.youtube.com/@abc")

    with col_b:
        with st.container(border=True):
            st.markdown("**계약 조건**")
            계약금액 = st.text_input("계약금액 (VAT 별도) *", placeholder="2,000,000")

            c1, c2 = st.columns(2)
            with c1:
                업로드일 = st.date_input("업로드 예정일 *", value=None)
            with c2:
                제작수량 = st.number_input("제작 수량 (편) *", min_value=1, value=1, step=1)

            st.markdown("**2차 활용 라이선스**")
            이차활용기간 = st.text_input("2차 활용 기간", placeholder="업로드일로부터 6개월")
            이차활용범위 = st.text_area("2차 활용 포함 범위", placeholder="자사 SNS 광고 소재 활용 가능 (유료 광고 집행 포함)", height=72)

        with st.container(border=True):
            st.markdown("**지급 & 계약일**")
            c3, c4 = st.columns(2)
            with c3:
                세금계산서발행일 = st.date_input("세금계산서 발행일", value=None)
            with c4:
                지급예정일 = st.date_input("지급 예정일", value=None)

            c5, c6, c7 = st.columns(3)
            with c5:
                은행명 = st.text_input("은행명", placeholder="카카오뱅크")
            with c6:
                계좌번호 = st.text_input("계좌번호", placeholder="3333-01-1234567")
            with c7:
                예금주 = st.text_input("예금주", placeholder="홍길동")

            계약일 = st.date_input("계약 서명일", value=date.today())

    st.markdown("")

    col_btn, _ = st.columns([1, 3])
    with col_btn:
        generate_clicked = st.button(
            ":material/description: 계약서 초안 생성",
            type="primary",
            disabled=not (수임인 and 캠페인명 and 계약금액),
        )

    if generate_clicked:
        missing = []
        if not 수임인: missing.append("수임인")
        if not 캠페인명: missing.append("캠페인명")
        if not 계약금액: missing.append("계약금액")
        if not 업로드일: missing.append("업로드 예정일")

        if missing:
            st.error(f"필수 항목을 입력해주세요: {', '.join(missing)}")
        else:
            data = {
                "수임인": 수임인,
                "계약자유형": 계약자유형,
                "이메일": 이메일,
                "캠페인명": 캠페인명,
                "주제": 주제,
                "채널명": 채널명,
                "채널URL": 채널URL,
                "유튜브링크": 유튜브링크 or 채널URL,
                "계약금액": 계약금액,
                "업로드일": str(업로드일) if 업로드일 else "",
                "제작수량": str(제작수량),
                "2차활용기간": 이차활용기간,
                "2차활용범위": 이차활용범위,
                "세금계산서발행일": str(세금계산서발행일) if 세금계산서발행일 else str(업로드일) if 업로드일 else "",
                "지급예정일": str(지급예정일) if 지급예정일 else "",
                "은행명": 은행명,
                "계좌번호": 계좌번호,
                "예금주": 예금주,
                "계약일": str(계약일) if 계약일 else str(date.today()),
            }
            data = {k: v for k, v in data.items() if v}

            with st.spinner("계약서 생성 중..."):
                try:
                    from generate_contract import fill_contract_bytes
                    doc_bytes = fill_contract_bytes(data, template_path=TEMPLATE)
                    filename = f"{수임인.replace(' ', '_')}_계약서_{datetime.now().strftime('%Y%m%d')}.docx"

                    st.session_state.history.insert(0, {
                        "name": 수임인,
                        "campaign": 캠페인명,
                        "filename": filename,
                        "created_at": datetime.now(),
                        "doc_bytes": doc_bytes,
                    })

                    st.success(":material/check_circle: 계약서 생성 완료!")
                    st.download_button(
                        label=":material/download: 계약서 다운로드",
                        data=doc_bytes,
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )
                    if 이메일:
                        st.info(f":material/mail: Gmail 초안을 만들려면 Claude에게 `/contract-influencer` 커맨드로 요청하세요. (수신: {이메일})")
                except Exception as e:
                    st.error(f"오류 발생: {e}")

# ════════════════════════════════════════════════════════
# TAB 2: 생성 내역
# ════════════════════════════════════════════════════════
with tab_list:
    st.markdown('<p class="section-title">생성된 계약서 목록</p>', unsafe_allow_html=True)

    history = st.session_state.history

    if not history:
        st.info("이 세션에서 생성된 계약서가 없습니다. 탭 1에서 생성해보세요.")
    else:
        today_count = sum(1 for h in history if h["created_at"].date() == date.today())
        with st.container(horizontal=True):
            st.metric("이번 세션", len(history), border=True)
            st.metric("오늘 생성", today_count, border=True)

        st.markdown("")

        rows = [
            {
                "인플루언서": h["name"],
                "캠페인": h["campaign"],
                "생성일시": h["created_at"].strftime("%Y-%m-%d %H:%M"),
                "파일명": h["filename"],
            }
            for h in history
        ]
        df = pd.DataFrame(rows)

        with st.container(border=True):
            selected = st.dataframe(
                df,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
                column_config={
                    "인플루언서": st.column_config.TextColumn(width="small"),
                    "캠페인": st.column_config.TextColumn(width="medium"),
                    "파일명": st.column_config.TextColumn(width="large"),
                },
            )

        if selected and selected["selection"]["rows"]:
            idx = selected["selection"]["rows"][0]
            chosen = history[idx]
            with st.container(border=True):
                st.markdown(f"**선택됨:** `{chosen['filename']}`")
                st.download_button(
                    label=":material/download: 이 계약서 다운로드",
                    data=chosen["doc_bytes"],
                    file_name=chosen["filename"],
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key=f"dl_{idx}",
                )
