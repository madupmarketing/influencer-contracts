import streamlit as st
import pandas as pd
import base64
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
if "ocr_bank" not in st.session_state:
    st.session_state.ocr_bank = {}
if "ocr_biz" not in st.session_state:
    st.session_state.ocr_biz = {}


# ── OCR 헬퍼 ──────────────────────────────────────────────
def ocr_image(image_bytes: bytes, image_type: str, task: str) -> dict:
    """이미지를 Claude로 읽어 구조화된 데이터 반환. 이미지는 메모리에서만 처리."""
    try:
        import anthropic
        api_key = st.secrets.get("ANTHROPIC_API_KEY", "") or __import__("os").environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            return {"error": "ANTHROPIC_API_KEY가 설정되지 않았습니다."}

        client = anthropic.Anthropic(api_key=api_key)
        b64 = base64.standard_b64encode(image_bytes).decode()

        if task == "bank":
            prompt = "이 통장 사본 이미지에서 은행명, 계좌번호, 예금주를 추출해줘. JSON으로만 응답: {\"은행명\": \"\", \"계좌번호\": \"\", \"예금주\": \"\"}"
        else:
            prompt = "이 사업자등록증 이미지에서 상호(회사명), 사업자등록번호, 사업장주소, 대표자성명을 추출해줘. JSON으로만 응답: {\"회사명\": \"\", \"사업자등록번호\": \"\", \"주소\": \"\", \"대표자\": \"\"}"

        media_type_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png"}
        media_type = media_type_map.get(image_type.lower(), "image/jpeg")

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            messages=[{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}},
                {"type": "text", "text": prompt},
            ]}],
        )
        import json
        text = response.content[0].text.strip()
        # JSON 추출
        m = re.search(r"\{.*\}", text, re.DOTALL)
        return json.loads(m.group(0)) if m else {"error": "파싱 실패"}
    except Exception as e:
        return {"error": str(e)}


# ── 2차 활용 기간 계산 ─────────────────────────────────────
def calc_license_end(upload_date: date, period_text: str):
    """'3개월', '6개월', '1년' 등 텍스트 + 업로드일 → 종료일 계산"""
    if not upload_date or not period_text:
        return None
    m = re.search(r"(\d+)\s*개월", period_text)
    if m:
        return upload_date + relativedelta(months=int(m.group(1)))
    m = re.search(r"(\d+)\s*[년year]", period_text)
    if m:
        return upload_date + relativedelta(years=int(m.group(1)))
    m = re.search(r"(\d+)\s*[주week]", period_text)
    if m:
        return upload_date + relativedelta(weeks=int(m.group(1)))
    return None


# ════════════════════════════════════════════════════════════
st.markdown("## :material/contract: 인플루언서 계약서 자동화")
st.caption("매드업 표준 계약서 기반 · 인플루언서 정보 입력 → 계약서 초안 자동 생성")
st.divider()

tab_new, tab_list = st.tabs([":material/add: 새 계약서 작성", ":material/folder_open: 생성 내역"])

with tab_new:
    # ── 기본 정보 + 채널 ──────────────────────────────────
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
            이차활용기간_raw = st.text_input("2차 활용 기간", placeholder="업로드일로부터 6개월")
            # 자동 계산 미리보기
            if 이차활용기간_raw and 업로드일:
                end = calc_license_end(업로드일, 이차활용기간_raw)
                if end:
                    st.caption(f"📅 {업로드일.strftime('%Y년 %m월 %d일')} ~ {end.strftime('%Y년 %m월 %d일')}")
                    이차활용기간 = f"{이차활용기간_raw} ({업로드일.strftime('%Y.%m.%d')} ~ {end.strftime('%Y.%m.%d')})"
                else:
                    이차활용기간 = 이차활용기간_raw
            else:
                이차활용기간 = 이차활용기간_raw

            이차활용범위 = st.text_area("2차 활용 포함 범위", placeholder="자사 SNS 광고 소재 활용 가능 (유료 광고 집행 포함)", height=68)

        with st.container(border=True):
            st.markdown("**지급 & 계약일**")
            c3, c4 = st.columns(2)
            with c3:
                세금계산서발행일 = st.date_input("세금계산서 발행일", value=None)
            with c4:
                지급예정일 = st.date_input("지급 예정일", value=None)

            # 통장 사본 OCR
            bank_file = st.file_uploader("통장 사본 업로드 (자동 입력)", type=["jpg", "jpeg", "png"], key="bank_upload")
            if bank_file:
                with st.spinner("통장 정보 읽는 중..."):
                    ext = bank_file.name.rsplit(".", 1)[-1]
                    result = ocr_image(bank_file.read(), ext, "bank")
                    bank_file = None  # 즉시 참조 해제
                if "error" not in result:
                    st.session_state.ocr_bank = result
                    st.success("자동 입력 완료 — 아래 내용을 확인해주세요")
                else:
                    st.error(result["error"])

            c5, c6, c7 = st.columns(3)
            with c5:
                은행명 = st.text_input("은행명", value=st.session_state.ocr_bank.get("은행명", ""), placeholder="카카오뱅크")
            with c6:
                계좌번호 = st.text_input("계좌번호", value=st.session_state.ocr_bank.get("계좌번호", ""), placeholder="3333-01-1234567")
            with c7:
                예금주 = st.text_input("예금주", value=st.session_state.ocr_bank.get("예금주", ""), placeholder="홍길동")

            계약일 = st.date_input("계약 서명일", value=date.today())

    # ── 수임인 상세 정보 ──────────────────────────────────
    st.markdown("")
    with st.expander("수임인 상세 정보 입력", expanded=False):
        if 계약자유형 == "개인":
            st.caption("개인 계약자 정보")
            ci1, ci2 = st.columns(2)
            with ci1:
                수임인_성명 = st.text_input("성명", placeholder="홍길동", key="p_name")
                수임인_주소 = st.text_input("주소", placeholder="서울시 강남구 ...", key="p_addr")
            with ci2:
                수임인_생년월일 = st.text_input("생년월일", placeholder="1990-01-01", key="p_birth")
        else:
            # 사업자등록증 OCR
            biz_file = st.file_uploader("사업자등록증 업로드 (자동 입력)", type=["jpg", "jpeg", "png"], key="biz_upload")
            if biz_file:
                with st.spinner("사업자 정보 읽는 중..."):
                    ext = biz_file.name.rsplit(".", 1)[-1]
                    result = ocr_image(biz_file.read(), ext, "biz")
                    biz_file = None
                if "error" not in result:
                    st.session_state.ocr_biz = result
                    st.success("자동 입력 완료 — 아래 내용을 확인해주세요")
                else:
                    st.error(result["error"])

            st.caption("사업자 계약자 정보")
            cb1, cb2 = st.columns(2)
            with cb1:
                수임인_회사명 = st.text_input("회사명", value=st.session_state.ocr_biz.get("회사명", ""), placeholder="주식회사 OO", key="b_company")
                수임인_등록번호 = st.text_input("사업자등록번호", value=st.session_state.ocr_biz.get("사업자등록번호", ""), placeholder="000-00-00000", key="b_regno")
            with cb2:
                수임인_주소 = st.text_input("사업장 주소", value=st.session_state.ocr_biz.get("주소", ""), placeholder="서울시 강남구 ...", key="b_addr")
                수임인_대표자 = st.text_input("대표자명", value=st.session_state.ocr_biz.get("대표자", ""), placeholder="홍길동", key="b_ceo")

    # ── 생성 버튼 ─────────────────────────────────────────
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
            # 수임인 상세 정보 수집
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
                    # OCR 캐시 초기화
                    st.session_state.ocr_bank = {}
                    st.session_state.ocr_biz = {}

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

# ════════════════════════════════════════════════════════════
# TAB 2: 생성 내역
# ════════════════════════════════════════════════════════════
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
