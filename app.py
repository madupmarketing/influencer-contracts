import streamlit as st
import pandas as pd
import re
from pathlib import Path
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

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

if "history" not in st.session_state:
    st.session_state.history = []


def calc_license_end(start: date, amount: int, unit: str) -> date:
    """시작일 포함 기간 계산 (7/1 + 3일 = 7/3)"""
    if unit == "일":
        return start + relativedelta(days=amount - 1)
    elif unit == "개월":
        return start + relativedelta(months=amount) - relativedelta(days=1)
    elif unit == "년":
        return start + relativedelta(years=amount) - relativedelta(days=1)
    return start


st.markdown("## :material/contract: 인플루언서 계약서 자동화")
st.caption("매드업 표준 계약서 기반 · 인플루언서 정보 입력 → 계약서 초안 자동 생성")
st.divider()

tab_new, tab_list = st.tabs([":material/add: 새 계약서 작성", ":material/folder_open: 생성 내역"])

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
            유튜브링크 = st.text_input("유튜브 링크", placeholder="https://www.youtube.com/@abc")

    with col_b:
        with st.container(border=True):
            st.markdown("**계약 조건**")
            계약금액 = st.text_input("계약금액 *", placeholder="2,000,000")

            c1, c2 = st.columns(2)
            with c1:
                업로드일 = st.date_input("업로드 예정일 *", value=None)
            with c2:
                제작수량 = st.number_input("제작 수량 (편) *", min_value=1, value=1, step=1)

            st.markdown("**2차 활용 라이선스**")
            lc1, lc2 = st.columns(2)
            with lc1:
                라이선스_시작일 = st.date_input("시작일", value=None, key="lic_start")
            with lc2:
                라이선스_종료일 = st.date_input("종료일", value=None, key="lic_end")

            # 기간 계산기
            with st.container(border=False):
                st.caption("기간 계산기 — 시작일 기준으로 종료일 자동 계산")
                dc1, dc2, dc3 = st.columns([2, 2, 1])
                with dc1:
                    기간_숫자 = st.number_input("기간", min_value=1, value=6, step=1, label_visibility="collapsed", key="dur_n")
                with dc2:
                    기간_단위 = st.selectbox("단위", ["개월", "일", "년"], label_visibility="collapsed", key="dur_unit")
                with dc3:
                    calc_clicked = st.button("계산", key="calc_btn", use_container_width=True)

            if calc_clicked:
                if 라이선스_시작일:
                    st.session_state.lic_end = calc_license_end(라이선스_시작일, 기간_숫자, 기간_단위)
                    st.rerun()
                else:
                    st.warning("시작일을 먼저 선택해주세요.")

            # 최종 기간 텍스트
            if 라이선스_시작일 and 라이선스_종료일:
                st.caption(f"📅 {라이선스_시작일.strftime('%Y년 %m월 %d일')} ~ {라이선스_종료일.strftime('%Y년 %m월 %d일')}")
                이차활용기간 = f"업로드일로부터 {기간_숫자}{기간_단위} ({라이선스_시작일.strftime('%Y.%m.%d')} ~ {라이선스_종료일.strftime('%Y.%m.%d')})"
            elif 라이선스_시작일:
                이차활용기간 = f"{라이선스_시작일.strftime('%Y.%m.%d')} ~"
            else:
                이차활용기간 = ""

            이차활용범위 = st.text_area("2차 활용 포함 범위", placeholder="자사 SNS 광고 소재 활용 가능 (유료 광고 집행 포함)", height=68)

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
    with st.expander("수임인 상세 정보 입력", expanded=True):
        if 계약자유형 == "개인":
            st.caption("개인 계약자 정보")
            ci1, ci2 = st.columns(2)
            with ci1:
                st.text_input("성명", placeholder="홍길동", key="p_name")
                st.text_input("주소", placeholder="서울시 강남구 ...", key="p_addr")
            with ci2:
                st.text_input("생년월일", placeholder="1990-01-01", key="p_birth")
        else:
            st.caption("사업자 계약자 정보")
            cb1, cb2 = st.columns(2)
            with cb1:
                st.text_input("회사명", placeholder="주식회사 OO", key="b_company")
                st.text_input("사업자등록번호", placeholder="000-00-00000", key="b_regno")
            with cb2:
                st.text_input("사업장 주소", placeholder="서울시 강남구 ...", key="b_addr")
                st.text_input("대표자명", placeholder="홍길동", key="b_ceo")

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
            if 계약자유형 == "개인":
                수임인_상세 = {
                    "수임인_성명": st.session_state.get("p_name", ""),
                    "수임인_주소": st.session_state.get("p_addr", ""),
                    "수임인_생년월일": st.session_state.get("p_birth", ""),
                }
            else:
                수임인_상세 = {
                    "수임인_회사명": st.session_state.get("b_company", ""),
                    "수임인_등록번호": st.session_state.get("b_regno", ""),
                    "수임인_주소": st.session_state.get("b_addr", ""),
                    "수임인_대표자": st.session_state.get("b_ceo", ""),
                }

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
                **수임인_상세,
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
                        st.info(f":material/mail: Gmail 초안 → Claude `/contract-influencer` 커맨드 (수신: {이메일})")
                except Exception as e:
                    st.error(f"오류 발생: {e}")

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
        rows = [{"인플루언서": h["name"], "캠페인": h["campaign"],
                 "생성일시": h["created_at"].strftime("%Y-%m-%d %H:%M"), "파일명": h["filename"]}
                for h in history]
        df = pd.DataFrame(rows)

        with st.container(border=True):
            selected = st.dataframe(df, hide_index=True, on_select="rerun", selection_mode="single-row",
                column_config={"인플루언서": st.column_config.TextColumn(width="small"),
                               "캠페인": st.column_config.TextColumn(width="medium"),
                               "파일명": st.column_config.TextColumn(width="large")})

        if selected and selected["selection"]["rows"]:
            idx = selected["selection"]["rows"][0]
            chosen = history[idx]
            with st.container(border=True):
                st.markdown(f"**선택됨:** `{chosen['filename']}`")
                st.download_button(label=":material/download: 이 계약서 다운로드",
                    data=chosen["doc_bytes"], file_name=chosen["filename"],
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key=f"dl_{idx}")
