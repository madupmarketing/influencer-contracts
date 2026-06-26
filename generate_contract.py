"""
인플루언서 계약서 자동 생성기
사용법: uv run python generate_contract.py --json data.json
"""
import zipfile, shutil, re, json, sys, argparse
from pathlib import Path
from datetime import datetime

TEMPLATE = Path(__file__).parent / "template" / "표준계약서_원본.docx"
OUTPUT_DIR = Path(__file__).parent / "output"

# 단락 ID → 필드 매핑 (원본 docx 분석 결과)
PARA = {
    "세금계산서발행일": "684ABF08",
    "지급예정일": "09947FEC",
    "업로드시점": "44385707",
    "은행정보": "6A5F2B8B",
    "제작수량": "0C18AEF2",
    "2차활용기간": "572FC0BE",
    "2차활용범위": "2FC2C33D",
    "채널정보": "1E311B5D",
    "유튜브링크": "7B8D3947",
    "계약건명": "3C5E7D4B",
    "캠페인명": "2042D2CF",
    "계약일": "6B40A275",
    # 수임인 서명 섹션
    "수임인_회사명": "060A83A8",
    "수임인_등록번호": "55C42044",
    "수임인_주소": "64569D1A",
    "수임인_대표자": "4AB07BD6",
}


def parse_date(s):
    d = datetime.strptime(s, "%Y-%m-%d")
    return str(d.year), str(d.month), str(d.day)


def get_para_range(xml, para_id):
    """paraId에 해당하는 <w:p> 태그의 (start, end) 인덱스 반환"""
    marker = f'w14:paraId="{para_id}"'
    idx = xml.find(marker)
    if idx == -1:
        return None, None
    p_start = xml.rfind("<w:p ", 0, idx)
    p_end = xml.find("</w:p>", idx) + 6
    return p_start, p_end


def replace_para_text(xml, para_id, new_text):
    """특정 paraId 단락의 텍스트를 new_text로 교체 (단락 서식 유지)"""
    p_start, p_end = get_para_range(xml, para_id)
    if p_start is None:
        return xml

    old_para = xml[p_start:p_end]

    # 여는 태그 추출
    p_tag = re.match(r"<w:p[^>]*>", old_para).group(0)

    # pPr 보존
    pPr_m = re.search(r"<w:pPr>.*?</w:pPr>", old_para, re.DOTALL)
    pPr = pPr_m.group(0) if pPr_m else ""

    # 첫 번째 rPr 보존 (글꼴 등)
    rPr_m = re.search(r"<w:rPr>(.*?)</w:rPr>", old_para, re.DOTALL)
    rPr = f"<w:rPr>{rPr_m.group(1)}</w:rPr>" if rPr_m else ""

    new_run = f'<w:r>{rPr}<w:t xml:space="preserve">{new_text}</w:t></w:r>'
    new_para = f"{p_tag}{pPr}{new_run}</w:p>"

    return xml[:p_start] + new_para + xml[p_end:]


def append_to_para_text(xml, para_id, suffix):
    """특정 paraId 단락의 마지막 텍스트 run에 suffix 추가"""
    p_start, p_end = get_para_range(xml, para_id)
    if p_start is None:
        return xml

    old_para = xml[p_start:p_end]

    # 마지막 <w:t> 태그 찾아서 값 추가
    last_t = list(re.finditer(r"<w:t([^>]*)>([^<]*)</w:t>", old_para))
    if not last_t:
        return xml

    m = last_t[-1]
    old_t = m.group(0)
    new_t = f'<w:t{m.group(1)}>{m.group(2)}{suffix}</w:t>'
    new_para = old_para[:m.start()] + new_t + old_para[m.end():]

    return xml[:p_start] + new_para + xml[p_end:]


def insert_run_to_para(xml, para_id, new_text, rPr_hint=""):
    """빈 단락에 새 텍스트 run 삽입"""
    p_start, p_end = get_para_range(xml, para_id)
    if p_start is None:
        return xml

    old_para = xml[p_start:p_end]
    p_tag = re.match(r"<w:p[^>]*>", old_para).group(0)
    pPr_m = re.search(r"<w:pPr>.*?</w:pPr>", old_para, re.DOTALL)
    pPr = pPr_m.group(0) if pPr_m else ""

    default_rPr = '<w:rPr><w:rFonts w:asciiTheme="majorHAnsi" w:eastAsiaTheme="majorHAnsi" w:hAnsiTheme="majorHAnsi" w:hint="eastAsia"/></w:rPr>'
    rPr = rPr_hint or default_rPr

    new_run = f"<w:r>{rPr}<w:t>{new_text}</w:t></w:r>"
    new_para = f"{p_tag}{pPr}{new_run}</w:p>"

    return xml[:p_start] + new_para + xml[p_end:]


def apply_replacements(xml, d):
    # 1. 수임인: 이름(채널명) 또는 사업자명(채널명)
    채널명 = d.get("채널명", "")
    display_name = f"{d['수임인']}({채널명})" if 채널명 else d["수임인"]
    xml = xml.replace("<w:t>[      ]</w:t>", f"<w:t>{display_name}</w:t>", 1)

    # 2. 계약건명 (빈 셀)
    if d.get("계약건명"):
        xml = insert_run_to_para(xml, PARA["계약건명"], d["계약건명"])

    # 2b. 캠페인명 (빈 셀)
    if d.get("캠페인명"):
        xml = insert_run_to_para(xml, PARA["캠페인명"], d["캠페인명"])

    # 3. 계약금액 + 유형별 주석
    if d.get("계약금액"):
        if d.get("계약자유형") == "개인":
            note = "  *3.3% 원천징수 차감 전 금액"
        else:
            note = "  *VAT 별도"
        xml = xml.replace("<w:t>0</w:t>", f"<w:t>{d['계약금액']}{note}</w:t>", 1)

    # 4. 세금계산서 발행일 (paraId=684ABF08)
    if d.get("세금계산서발행일"):
        y, m, day = parse_date(d["세금계산서발행일"])
        xml = replace_para_text(
            xml, PARA["세금계산서발행일"],
            f"  {y}년 {m}월 {day}일 (영상 업로드일) "
        )

    # 5. 지급예정일 (paraId=09947FEC)
    if d.get("지급예정일"):
        y, m, day = parse_date(d["지급예정일"])
        xml = replace_para_text(
            xml, PARA["지급예정일"],
            f"20{y[2:]}년 {m}월 {day}일"
        )

    # 6. 은행 정보 (paraId=6A5F2B8B)
    bank = f"{d.get('은행명','')} / {d.get('계좌번호','')} / {d.get('예금주','')}"
    xml = replace_para_text(xml, PARA["은행정보"], bank)

    # 7. 주제 (주제:- 에서 :- 를 ': 주제값' 으로)
    if d.get("주제"):
        xml = xml.replace("<w:t>:-</w:t>", f"<w:t>: {d['주제']}</w:t>", 1)

    # 8. 업로드 시점 (paraId=44385707)
    if d.get("업로드일"):
        y, m, day = parse_date(d["업로드일"])
        xml = replace_para_text(
            xml, PARA["업로드시점"],
            f"업로드 시점 : {y}년 {m}월 {day}일 "
        )

    # 9. 제작 수량 (paraId=0C18AEF2)
    if d.get("제작수량"):
        xml = replace_para_text(
            xml, PARA["제작수량"],
            f"제작 수량 : {d['제작수량']}편"
        )

    # 10. 2차 활용 기간 (paraId=572FC0BE) - 끝에 값 추가
    if d.get("2차활용기간"):
        xml = append_to_para_text(xml, PARA["2차활용기간"], d["2차활용기간"])

    # 11. 2차 활용 포함 범위 (paraId=2FC2C33D) - 끝에 값 추가
    if d.get("2차활용범위"):
        xml = append_to_para_text(xml, PARA["2차활용범위"], " " + d["2차활용범위"])

    # 12. 채널 정보 (paraId=1E311B5D): 채널명 + URL
    channel = d.get("채널명", "")
    channel_url = d.get("채널URL", "")
    if channel or channel_url:
        xml = replace_para_text(
            xml, PARA["채널정보"],
            f"{channel}  {channel_url}"
        )

    # 13. 유튜브 링크 (paraId=7B8D3947): '유튜브 : 링크 삽입' → '유튜브 : URL'
    if d.get("유튜브링크"):
        xml = replace_para_text(
            xml, PARA["유튜브링크"],
            f"유튜브 :  {d['유튜브링크']}"
        )

    # 14. 계약일 (paraId=6F8B9D0D)
    if d.get("계약일"):
        y, m, day = parse_date(d["계약일"])
        xml = replace_para_text(
            xml, PARA["계약일"],
            f"{y}년  {m}월  {day}일"
        )

    # 15. 수임인 서명 섹션 (계약서 하단)
    is_individual = d.get("계약자유형", "개인") == "개인"
    if is_individual:
        name = d.get("수임인_성명") or d.get("수임인", "")
        xml = replace_para_text(xml, PARA["수임인_회사명"], f"성    명 : {name}")
        if d.get("수임인_생년월일"):
            xml = replace_para_text(xml, PARA["수임인_등록번호"], f"생년월일 : {d['수임인_생년월일']}")
        if d.get("수임인_주소"):
            xml = replace_para_text(xml, PARA["수임인_주소"], f"주    소 : {d['수임인_주소']}")
        xml = replace_para_text(xml, PARA["수임인_대표자"], f"서    명 : {name}  (인)")
    else:
        company = d.get("수임인_회사명") or d.get("수임인", "")
        xml = replace_para_text(xml, PARA["수임인_회사명"], f"회 사 명 : {company}")
        if d.get("수임인_등록번호"):
            xml = replace_para_text(xml, PARA["수임인_등록번호"], f"등록번호 : {d['수임인_등록번호']}")
        if d.get("수임인_주소"):
            xml = replace_para_text(xml, PARA["수임인_주소"], f"주    소 : {d['수임인_주소']}")
        if d.get("수임인_대표자"):
            xml = replace_para_text(xml, PARA["수임인_대표자"], f"대 표 자 : {d['수임인_대표자']}  (인)")

    return xml


COMMENT_PARTS = [
    "word/comments.xml", "word/commentsExtended.xml",
    "word/commentsIds.xml", "word/commentsExtensible.xml",
]


def strip_comments(contents, names):
    """문서 내 모든 댓글(코멘트) 제거: 마커·런·파트·관계·콘텐츠타입 정리"""
    # 1. document.xml 에서 댓글 마커/런 제거
    doc = contents["word/document.xml"].decode("utf-8")
    doc = re.sub(r"<w:commentRangeStart[^>]*/>", "", doc)
    doc = re.sub(r"<w:commentRangeEnd[^>]*/>", "", doc)
    # commentReference 를 감싼 <w:r> ... </w:r> 통째로 제거
    doc = re.sub(
        r"<w:r\b[^>]*>(?:(?!</w:r>).)*?<w:commentReference[^>]*/>(?:(?!</w:r>).)*?</w:r>",
        "", doc, flags=re.DOTALL,
    )
    contents["word/document.xml"] = doc.encode("utf-8")

    # 2. 댓글 관련 파트 파일 삭제
    for part in COMMENT_PARTS:
        contents.pop(part, None)
        if part in names:
            names.remove(part)

    # 3. document.xml.rels 에서 댓글 관계 제거
    rels_key = "word/_rels/document.xml.rels"
    if rels_key in contents:
        rels = contents[rels_key].decode("utf-8")
        rels = re.sub(r"<Relationship\b[^>]*comment[^>]*/>", "", rels, flags=re.IGNORECASE)
        contents[rels_key] = rels.encode("utf-8")

    # 4. [Content_Types].xml 에서 댓글 Override 제거
    ct_key = "[Content_Types].xml"
    if ct_key in contents:
        ct = contents[ct_key].decode("utf-8")
        ct = re.sub(r"<Override\b[^>]*comment[^>]*/>", "", ct, flags=re.IGNORECASE)
        contents[ct_key] = ct.encode("utf-8")

    return contents, names


def fill_contract_bytes(data, template_path=None):
    """계약서를 메모리에서 생성해 bytes 반환 (디스크 불필요)"""
    import io
    tpl = Path(template_path) if template_path else TEMPLATE

    with zipfile.ZipFile(tpl, "r") as zin:
        names = zin.namelist()
        contents = {name: zin.read(name) for name in names}

    xml = contents["word/document.xml"].decode("utf-8")
    xml = apply_replacements(xml, data)
    contents["word/document.xml"] = xml.encode("utf-8")

    # 템플릿에 달린 댓글 전부 제거
    contents, names = strip_comments(contents, names)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zout:
        # [Content_Types].xml 반드시 첫 번째
        priority = ["[Content_Types].xml", "_rels/.rels"]
        ordered = [n for n in priority if n in contents]
        ordered += [n for n in names if n not in priority]
        for name in ordered:
            zout.writestr(name, contents[name])

    return buf.getvalue()


def fill_contract(data):
    name = data["수임인"].replace(" ", "_")
    today = datetime.now().strftime("%Y%m%d")
    out_path = OUTPUT_DIR / f"{name}_계약서_{today}.docx"
    OUTPUT_DIR.mkdir(exist_ok=True)

    doc_bytes = fill_contract_bytes(data)
    out_path.write_bytes(doc_bytes)
    return out_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", help="JSON 문자열")
    parser.add_argument("--json", help="JSON 파일 경로")
    args = parser.parse_args()

    if args.json:
        with open(args.json, encoding="utf-8") as f:
            data = json.load(f)
    elif args.data:
        data = json.loads(args.data)
    else:
        print("ERROR: --data 또는 --json 필요")
        sys.exit(1)

    out = fill_contract(data)
    print(f"OUTPUT:{out}")


if __name__ == "__main__":
    main()
