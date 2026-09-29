import streamlit as st
import pandas as pd
import fitz  # PyMuPDF (PDF 이미지 추출용)
from PIL import Image
import io
from datetime import datetime

# 페이지 기본 설정
st.set_page_config(
    page_title="현장 지적사항 및 조치결과 관리 시스템",
    page_icon="🏗️",
    layout="wide"
)

# -----------------------------------------------------------------------------
# 세션 상태(Session State) 초기화
# -----------------------------------------------------------------------------
if "issues" not in st.session_state:
    # 지적사항 데이터 구조 정의
    st.session_state.issues = []

if "extracted_images" not in st.session_state:
    st.session_state.extracted_images = []

# -----------------------------------------------------------------------------
# 헬퍼 함수: PDF에서 이미지 추출
# -----------------------------------------------------------------------------
def extract_images_from_pdf(pdf_file):
    images = []
    try:
        doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
        for page_index in range(len(doc)):
            page = doc[page_index]
            image_list = page.get_images(full=True)
            
            for img_index, img in enumerate(image_list):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]
                
                # PIL Image로 변환
                image = Image.open(io.BytesIO(image_bytes))
                images.append({
                    "id": f"P{page_index+1}_IMG{img_index+1}",
                    "page": page_index + 1,
                    "image": image,
                    "ext": image_ext
                })
    except Exception as e:
        st.error(f"PDF 이미지 추출 중 오류가 발생했습니다: {e}")
    return images

# -----------------------------------------------------------------------------
# 메인 타이틀 및 사이드바
# -----------------------------------------------------------------------------
st.title("🏗️ 점검결과 지적사항 및 조치결과 관리 시스템")
st.markdown("PDF 점검보고서로부터 지적사진을 추출하고, **지적등록 ➔ 조치등록 ➔ 최종승인** 프로세스를 진행합니다.")

st.sidebar.header("📋 메뉴 선택")
menu = st.sidebar.radio(
    "업무 단계를 선택하세요:",
    ["1. 지적사항 등록 (PDF 업로드)", "2. 조치결과 등록", "3. 최종 승인 검토", "4. 전체 현황 대시보드"]
)

# -----------------------------------------------------------------------------
# 1단계: 지적사항 등록 (PDF 업로드 & 이미지 추출)
# -----------------------------------------------------------------------------
if menu == "1. 지적사항 등록 (PDF 업로드)":
    st.subheader("1️⃣ PDF 점검결과 업로드 및 지적사항 등록")
    
    uploaded_file = st.file_uploader("점검결과 PDF 파일을 업로드하세요", type=["pdf"])
    
    if uploaded_file is not None:
        if st.button("PDF에서 지적사진 추출하기"):
            with st.spinner("PDF 문서 내 이미지를 분석 중입니다..."):
                extracted = extract_images_from_pdf(uploaded_file)
                st.session_state.extracted_images = extracted
                st.success(f"총 {len(extracted)}개의 이미지를 추출했습니다.")

    # 추출된 이미지가 있을 경우 등록 폼 제공
    if st.session_state.extracted_images:
        st.write("---")
        st.markdown("### 📸 추출된 사진을 선택하여 지적사항 등록")
        
        # 이미지 선택
        img_options = [f"페이지 {img['page']} - 이미지 {img['id']}" for img in st.session_state.extracted_images]
        selected_idx = st.selectbox("등록할 사진을 선택하세요", range(len(img_options)), format_func=lambda x: img_options[x])
        
        selected_img_data = st.session_state.extracted_images[selected_idx]
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.image(selected_img_data["image"], caption=f"선택된 이미지 ({selected_img_data['id']})", use_column_width=True)
            
        with col2:
            with st.form(key="register_form", clear_on_submit=True):
                location = st.text_input("지적 위치 (예: 101동 3층 슬래브)")
                description = st.text_area("지적 내용 (예: 철근 간격 미준수 및 콘크리트 피복 두께 부족)")
                assigned_to = st.text_input("담당자 / 협력사 (예: OO건설 / 김창호 팀장)")
                priority = st.selectbox("긴급도", ["보통", "긴급", "매우 긴급"])
                
                submit_button = st.form_submit_button(label="지적사항 등록 완료")
                
                if submit_button:
                    if not location or not description:
                        st.warning("위치와 지적 내용을 입력해주세요.")
                    else:
                        new_id = len(st.session_state.issues) + 1
                        new_issue = {
                            "id": new_id,
                            "location": location,
                            "description": description,
                            "assigned_to": assigned_to,
                            "priority": priority,
                            "before_image": selected_img_data["image"],
                            "after_image": None,
                            "action_description": "",
                            "status": "조치대기",  # 상태: 조치대기 -> 조치완료 -> 승인완료 (or 보완요청)
                            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "action_date": "",
                            "approval_comment": ""
                        }
                        st.session_state.issues.append(new_issue)
                        st.success(f"지적사항 No.{new_id} 번이 등록되었습니다. (조치대기 상태)")

# -----------------------------------------------------------------------------
# 2단계: 조치결과 등록
# -----------------------------------------------------------------------------
elif menu == "2. 조치결과 등록":
    st.subheader("2️⃣ 현장 조치결과 등록")
    
    # 조치대기 또는 보완요청 항목 추출
    pending_issues = [i for i in st.session_state.issues if i["status"] in ["조치대기", "보완요청"]]
    
    if not pending_issues:
        st.info("현재 조치 등록이 필요한 지적사항이 없습니다.")
    else:
        issue_labels = [f"No.{i['id']} | 위치: {i['location']} | 상태: {i['status']}" for i in pending_issues]
        selected_issue_idx = st.selectbox("조치 등록할 지적건을 선택하세요", range(len(issue_labels)), format_func=lambda x: issue_labels[x])
        
        target_issue = pending_issues[selected_issue_idx]
        
        st.write("---")
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("**[지적 사진 및 정보]**")
            st.image(target_issue["before_image"], use_column_width=True)
            st.write(f"**위치:** {target_issue['location']}")
            st.write(f"**지적내용:** {target_issue['description']}")
            st.write(f"**담당자:** {target_issue['assigned_to']}")
            if target_issue["status"] == "보완요청":
                st.error(f"**보완요청 사유:** {target_issue['approval_comment']}")
                
        with col2:
            st.markdown("**[조치 결과 입력]**")
            uploaded_after_img = st.file_uploader("조치후 사진을 업로드하세요", type=["jpg", "jpeg", "png"])
            action_desc = st.text_area("조치 내용 상세 입력", value=target_issue["action_description"])
            
            if st.button("조치결과 제출하기"):
                if uploaded_after_img is None and target_issue["after_image"] is None:
                    st.warning("조치후 사진을 업로드해주세요.")
                elif not action_desc:
                    st.warning("조치내용을 입력해주세요.")
                else:
                    # 원본 session_state 항목 업데이트
                    for issue in st.session_state.issues:
                        if issue["id"] == target_issue["id"]:
                            if uploaded_after_img:
                                issue["after_image"] = Image.open(uploaded_after_img)
                            issue["action_description"] = action_desc
                            issue["status"] = "조치완료"
                            issue["action_date"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                            break
                    st.success(f"No.{target_issue['id']} 건의 조치결과가 등록되었습니다. (승인대기 상태 전환)")
                    st.rerun()

# -----------------------------------------------------------------------------
# 3단계: 최종 승인 검토
# -----------------------------------------------------------------------------
elif menu == "3. 최종 승인 검토":
    st.subheader("3️⃣ 조치결과 최종 승인 및 검토")
    
    # 조치완료(승인대기) 항목 추출
    review_issues = [i for i in st.session_state.issues if i["status"] == "조치완료"]
    
    if not review_issues:
        st.info("현재 승인 검토 대기 중인 항목이 없습니다.")
    else:
        issue_labels = [f"No.{i['id']} | 위치: {i['location']} | 담당: {i['assigned_to']}" for i in review_issues]
        selected_idx = st.selectbox("검토할 지적건을 선택하세요", range(len(issue_labels)), format_func=lambda x: issue_labels[x])
        
        target_issue = review_issues[selected_idx]
        
        st.write("---")
        st.markdown(f"### 📌 No.{target_issue['id']} - {target_issue['location']}")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("지적 전 (Before)")
            st.image(target_issue["before_image"], use_column_width=True)
            st.write(f"**지적 내용:** {target_issue['description']}")
            
        with col2:
            st.subheader("조치 후 (After)")
            if target_issue["after_image"]:
                st.image(target_issue["after_image"], use_column_width=True)
            st.write(f"**조치 내용:** {target_issue['action_description']}")
            st.write(f"**조치 일시:** {target_issue['action_date']}")

        st.write("---")
        st.markdown("### 📝 승인 여부 결정")
        comment = st.text_input("검토 의견 / 보완지시 사항", key="review_comment")
        
        col_app, col_rej = st.columns([1, 1])
        
        with col_app:
            if st.button("✅ 승인 완료", use_container_width=True):
                for issue in st.session_state.issues:
                    if issue["id"] == target_issue["id"]:
                        issue["status"] = "승인완료"
                        issue["approval_comment"] = comment if comment else "승인됨"
                        break
                st.success(f"No.{target_issue['id']} 건이 최종 승인되었습니다.")
                st.rerun()
                
        with col_rej:
            if st.button("❌ 보완 요청 (반려)", use_container_width=True):
                if not comment:
                    st.warning("보완 요청 시에는 사유(의견)를 작성해야 합니다.")
                else:
                    for issue in st.session_state.issues:
                        if issue["id"] == target_issue["id"]:
                            issue["status"] = "보완요청"
                            issue["approval_comment"] = comment
                            break
                    st.error(f"No.{target_issue['id']} 건에 대해 보완을 요청했습니다.")
                    st.rerun()

# -----------------------------------------------------------------------------
# 4단계: 전체 현황 대시보드
# -----------------------------------------------------------------------------
elif menu == "4. 전체 현황 대시보드":
    st.subheader("4️⃣ 지적사항 및 조치결과 전체 현황판")
    
    if not st.session_state.issues:
        st.info("등록된 지적사항이 없습니다.")
    else:
        total_cnt = len(st.session_state.issues)
        wait_cnt = len([i for i in st.session_state.issues if i["status"] == "조치대기"])
        action_cnt = len([i for i in st.session_state.issues if i["status"] == "조치완료"])
        reject_cnt = len([i for i in st.session_state.issues if i["status"] == "보완요청"])
        approved_cnt = len([i for i in st.session_state.issues if i["status"] == "승인완료"])
        
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("전체 건수", f"{total_cnt}건")
        m2.metric("조치 대기", f"{wait_cnt}건")
        m3.metric("승인 대기", f"{action_cnt}건")
        m4.metric("보완 요청", f"{reject_cnt}건")
        m5.metric("최종 승인", f"{approved_cnt}건")
        
        st.write("---")
        
        # 목록 데이터프레임 생성
        data = []
        for i in st.session_state.issues:
            data.append({
                "번호": i["id"],
                "위치": i["location"],
                "지적내용": i["description"],
                "담당자": i["assigned_to"],
                "상태": i["status"],
                "등록일": i["created_at"],
                "검토의견": i["approval_comment"]
            })
        
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)