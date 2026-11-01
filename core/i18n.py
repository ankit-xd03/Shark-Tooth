"""Internationalization (i18n) for CivicPilot AI: English, Hindi (हिन्दी), and Hinglish.

Design adopted from the team's earlier i18n prototype; keys and text are written for this
app's UI chrome only. Field labels, portal pages, log lines and values sent to the portal
stay in the portal's language on purpose. To add a string: give it a key here with en/hi/
hinglish text and use t(key) or t(key, **placeholders) in app.py. To add a language: add
its code and display name to LANGUAGES, then fill the new text for every key and STAGE_NAMES.
"""
LANGUAGES = {"en": "English", "hi": "हिन्दी", "hinglish": "Hinglish"}

TRANSLATIONS = {
    "app_title": {
        "en": "🏛️ CivicPilot AI",
        "hi": "🏛️ सिविकपायलट एआई (CivicPilot AI)",
        "hinglish": "🏛️ CivicPilot AI"},
    "app_caption": {
        "en": "Autonomous public-service assistant · scholarship, licence and LPG-subsidy workflows",
        "hi": "स्वायत्त जन-सेवा सहायक · छात्रवृत्ति, लाइसेंस और एलपीजी-सब्सिडी प्रक्रियाएँ",
        "hinglish": "Autonomous public-service assistant · scholarship, licence aur LPG-subsidy workflows"},
    "proto_banner": {
        "en": "Prototype: runs against a **local mock portal** with **fictional data only**. "
              "It is not connected to any real government system.",
        "hi": "प्रोटोटाइप: केवल **काल्पनिक डेटा** के साथ एक **लोकल मॉक पोर्टल** पर चलता है। यह किसी वास्तविक "
              "सरकारी प्रणाली से जुड़ा नहीं है।",
        "hinglish": "Prototype: **Local mock portal** par **fictional data** ke saath chalta hai. Real government "
                    "system se connected nahi hai."},
    "demo_warning": {
        "en": "**Demo mode:** no LLM key configured. Requests are parsed by a deterministic parser and the "
              "browser agent uses rule-based navigation.",
        "hi": "**डेमो मोड:** कोई LLM कुंजी कॉन्फ़िगर नहीं है। अनुरोध एक नियम-आधारित पार्सर द्वारा संसाधित किए जाते "
              "हैं और ब्राउज़र एजेंट नियम-आधारित नेविगेशन उपयोग करता है।",
        "hinglish": "**Demo mode:** koi LLM key set nahi hai. Requests rule-based parser se parse hote hain aur "
                    "browser agent rule-based navigation use karta hai."},
    "lang_picker": {
        "en": "🌐 Language / भाषा",
        "hi": "🌐 भाषा चयन (Language)",
        "hinglish": "🌐 Language chunein"},
    "progress": {
        "en": "Progress", "hi": "प्रगति", "hinglish": "Progress"},
    "stage_progress": {
        "en": "Stage {n} of 5", "hi": "चरण {n} / 5", "hinglish": "Stage {n} of 5"},
    "mode_llm": {
        "en": "🟢 LLM extraction + navigation",
        "hi": "🟢 LLM निष्कर्षण + नेविगेशन",
        "hinglish": "🟢 LLM extraction + navigation"},
    "mode_demo": {
        "en": "🟡 DEMO MODE (deterministic parser, rule-based navigation)",
        "hi": "🟡 डेमो मोड (नियम-आधारित पार्सर, नियम-आधारित नेविगेशन)",
        "hinglish": "🟡 DEMO MODE (deterministic parser, rule-based navigation)"},
    "portal_caption": {
        "en": "Mock portal: {url}", "hi": "मॉक पोर्टल: {url}", "hinglish": "Mock portal: {url}"},
    "activity_log": {
        "en": "Activity log", "hi": "गतिविधि लॉग", "hinglish": "Activity log"},
    "no_activity": {
        "en": "No activity yet", "hi": "अभी कोई गतिविधि नहीं", "hinglish": "Abhi koi activity nahi"},
    "past_apps": {
        "en": "Past demo applications", "hi": "पिछले डेमो आवेदन", "hinglish": "Past demo applications"},
    "nothing_yet": {
        "en": "Nothing submitted yet.", "hi": "अभी कुछ जमा नहीं हुआ है।", "hinglish": "Abhi kuch submit nahi hua."},
    "start_over": {
        "en": "Start over", "hi": "नया आवेदन शुरू करें", "hinglish": "Naye sire se shuru karein"},
    "submitted_ok": {
        "en": "Submitted. The mock portal confirmed your application.",
        "hi": "जमा हो गया। मॉक पोर्टल ने आपका आवेदन स्वीकार कर लिया है।",
        "hinglish": "Submit ho gaya. Mock portal ne aapka application confirm kar diya hai."},
    "app_id": {
        "en": "Application ID", "hi": "आवेदन आईडी", "hinglish": "Application ID"},
    "status_at_submit": {
        "en": "Status at submission", "hi": "जमा के समय की स्थिति", "hinglish": "Status at submission"},
    "submitted_at": {
        "en": "Submitted at (UTC)", "hi": "जमा करने का समय (UTC)", "hinglish": "Submitted at (UTC)"},
    "live_tracking": {
        "en": "Live tracking", "hi": "लाइव ट्रैकिंग", "hinglish": "Live tracking"},
    "portal_status_now": {
        "en": "Portal status now", "hi": "पोर्टल की वर्तमान स्थिति", "hinglish": "Portal status abhi"},
    "tracking_caption": {
        "en": "Reference {ref} · read directly from the portal's tracking page by the browser agent.",
        "hi": "संदर्भ {ref} · ब्राउज़र एजेंट द्वारा पोर्टल के ट्रैकिंग पृष्ठ से सीधे पढ़ा गया।",
        "hinglish": "Reference {ref} · browser agent ne portal ke tracking page se seedha padha hai."},
    "refresh_status": {
        "en": "Refresh status", "hi": "स्थिति रीफ़्रेश करें", "hinglish": "Status refresh karein"},
    "tracking_spinner": {
        "en": "The agent is opening the portal tracking page…",
        "hi": "एजेंट पोर्टल का ट्रैकिंग पृष्ठ खोल रहा है…",
        "hinglish": "Agent portal ka tracking page khol raha hai…"},
    "status_flow_caption": {
        "en": "Official statuses progress over time: SUBMITTED → UNDER REVIEW → APPROVED.",
        "hi": "आधिकारिक स्थितियाँ समय के साथ बढ़ती हैं: SUBMITTED → UNDER REVIEW → APPROVED.",
        "hinglish": "Official statuses time ke saath aage badhte hain: SUBMITTED → UNDER REVIEW → APPROVED."},
    "dl_receipt_json": {
        "en": "Download receipt (JSON)", "hi": "रसीद डाउनलोड करें (JSON)", "hinglish": "Receipt download karein (JSON)"},
    "dl_receipt_txt": {
        "en": "Download receipt (text)", "hi": "रसीद डाउनलोड करें (text)", "hinglish": "Receipt download karein (text)"},
    "dl_audit": {
        "en": "Download audit report (HTML)", "hi": "ऑडिट रिपोर्ट डाउनलोड करें (HTML)",
        "hinglish": "Audit report download karein (HTML)"},
    "raw_record": {
        "en": "Raw portal record", "hi": "पोर्टल का कच्चा रिकॉर्ड", "hinglish": "Raw portal record"},
    "review_header": {
        "en": "Review the completed application", "hi": "पूर्ण आवेदन की समीक्षा करें",
        "hinglish": "Complete hue application ko review karein"},
    "prep_ok": {
        "en": "The agent filled the mock portal form and the portal accepted the values for review.",
        "hi": "एजेंट ने मॉक पोर्टल फ़ॉर्म भर दिया और पोर्टल ने मूल्यों को समीक्षा हेतु स्वीकार कर लिया।",
        "hinglish": "Agent ne mock portal form bhar diya aur portal ne values review ke liye accept kar li."},
    "approve_header": {
        "en": "Confirm final submission", "hi": "अंतिम जमा की पुष्टि करें", "hinglish": "Final submission confirm karein"},
    "otp_default": {
        "en": "This portal requires a one-time password (OTP).",
        "hi": "इस पोर्टल को एक बार का पासवर्ड (OTP) चाहिए।",
        "hinglish": "Is portal ko one-time password (OTP) chahiye."},
    "otp_caption": {
        "en": "CivicPilot has paused. The agent never reads or guesses the code — it only types the code that "
              "YOU enter here.",
        "hi": "CivicPilot रुक गया है। एजेंट कभी कोड नहीं पढ़ता या अनुमान नहीं लगाता — वह केवल वही कोड टाइप करता "
              "है जो आप यहाँ दर्ज करते हैं।",
        "hinglish": "CivicPilot pause ho gaya hai. Agent code kabhi padhta ya guess nahi karta — wahi code type "
                    "karta hai jo AAP yahan enter karte ho."},
    "sms_inbox": {
        "en": "Open the simulated SMS inbox", "hi": "सिम्युलेटेड SMS इनबॉक्स खोलें",
        "hinglish": "Simulated SMS inbox kholen"},
    "otp_input": {
        "en": "6-digit OTP from the SMS inbox", "hi": "SMS इनबॉक्स से 6-अंकों का OTP",
        "hinglish": "SMS inbox se 6-digit OTP"},
    "verify_otp": {
        "en": "Verify OTP and continue", "hi": "OTP सत्यापित करें और आगे बढ़ें",
        "hinglish": "OTP verify karein aur aage badhein"},
    "otp_spinner": {
        "en": "The agent is entering your code in the portal…",
        "hi": "एजेंट आपका कोड पोर्टल में दर्ज कर रहा है…",
        "hinglish": "Agent aapka code portal mein enter kar raha hai…"},
    "rejected_prefix": {
        "en": "The portal did not accept the application: {msg}",
        "hi": "पोर्टल ने आवेदन स्वीकार नहीं किया: {msg}",
        "hinglish": "Portal ne application accept nahi ki: {msg}"},
    "uncertain_hint": {
        "en": "{msg} Do not resubmit yet: check what the portal recorded first.",
        "hi": "{msg} अभी दोबारा जमा न करें: पहले जाँचें कि पोर्टल ने क्या दर्ज किया है।",
        "hinglish": "{msg} Abhi dobara submit mat karein: pehle check karein portal ne kya record kiya hai."},
    "check_status_btn": {
        "en": "Check portal status", "hi": "पोर्टल स्थिति जाँचें", "hinglish": "Portal status check karein"},
    "confirm_checkbox": {
        "en": "I have reviewed these details and authorize CivicPilot to submit this application to the mock portal.",
        "hi": "मैंने ये विवरण जाँच लिए हैं और CivicPilot को यह आवेदन मॉक पोर्टल पर जमा करने की अनुमति देता/देती हूँ।",
        "hinglish": "Maine ye details review kar li hain aur CivicPilot ko is application ko mock portal par "
                    "submit karne ka authorization de raha/rahi hoon."},
    "submit": {
        "en": "Submit application", "hi": "आवेदन जमा करें", "hinglish": "Application submit karein"},
    "submit_spinner": {
        "en": "Submitting via browser…", "hi": "ब्राउज़र के माध्यम से जमा किया जा रहा है…",
        "hinglish": "Browser ke through submit ho raha hai…"},
    "edit": {
        "en": "Edit details", "hi": "विवरण संपादित करें", "hinglish": "Details edit karein"},
    "continue": {
        "en": "Continue to approval", "hi": "स्वीकृति की ओर बढ़ें", "hinglish": "Approval ke liye aage badhein"},
    "h1": {
        "en": "1 · Tell me what you need", "hi": "1 · बताइए आपको क्या चाहिए",
        "hinglish": "1 · Bataiye aapko kya service chahiye"},
    "service": {
        "en": "Service", "hi": "सरकारी सेवा", "hinglish": "Service"},
    "request_label": {
        "en": "Describe the application in plain English (or Hindi / Hinglish)",
        "hi": "अपना अनुरोध अंग्रेज़ी, हिंदी या हिंग्लिश में लिखें",
        "hinglish": "Apni requirement plain English / Hindi / Hinglish mein likhein"},
    "request_placeholder": {
        "en": "e.g. I'm Aarav Sharma, 3rd year B.Tech student at Riverdale Institute of Technology. Please help "
              "me apply for the merit scholarship. Family income is 3.5 lakh, CGPA 8.4.  "
              "Or: Mujhe scholarship ke liye apply karna hai, income 3.5 lakh hai, CGPA 8.4.  "
              "Or: Renew my driving licence AS0120200012345, it expires on 15/12/2026.",
        "hi": "उदा. मैं आरव शर्मा, रिवरडेल इंस्टीट्यूट ऑफ़ टेक्नोलॉजी में बी.टेक तृतीय वर्ष का छात्र हूँ। कृपया मेरी "
              "छात्रवृत्ति के आवेदन में सहायता करें। वार्षिक आय 3.5 लाख, सीजीपीए 8.4।  "
              "या: मेरा ड्राइविंग लाइसेंस AS0120200012345 नवीनीकृत करें, यह 15/12/2026 को समाप्त होता है।",
        "hinglish": "e.g. Main Aarav Sharma, Riverdale Institute of Technology mein 3rd year B.Tech student hoon. "
                    "Merit scholarship ke liye apply karna hai. Family income 3.5 lakh hai, CGPA 8.4.  "
                    "Ya: Mera driving licence AS0120200012345 renew karwana hai, 15/12/2026 ko expire hota hai."},
    "h2": {
        "en": "2 · Applicant profile (fictional data)", "hi": "2 · आवेदक विवरण (काल्पनिक डेटा)",
        "hinglish": "2 · Applicant profile (fictional data)"},
    "h3": {
        "en": "3 · Preparation summary", "hi": "3 · तैयारी का सारांश", "hinglish": "3 · Preparation summary"},
    "doc_expander": {
        "en": "📎 Add details from a document (marksheet / income certificate / licence copy)",
        "hi": "📎 दस्तावेज़ से विवरण जोड़ें (मार्कशीट / आय प्रमाण पत्र / लाइसेंस प्रति)",
        "hinglish": "📎 Document se details add karein (marksheet / income certificate / licence copy)"},
    "doc_caption": {
        "en": "Text PDFs are read locally in demo mode. Scans and photos need a vision-capable LLM key. Every "
              "value shows its source and can be edited before anything is submitted.",
        "hi": "डेमो मोड में टेक्स्ट PDF स्थानीय रूप से पढ़े जाते हैं। स्कैन और फ़ोटो के लिए विज़न-सक्षम LLM कुंजी "
              "चाहिए। हर मूल्य अपना स्रोत दिखाता है और जमा करने से पहले संपादित किया जा सकता है।",
        "hinglish": "Text PDFs demo mode mein locally padhe jaate hain. Scans aur photos ke liye vision-capable "
                    "LLM key chahiye. Har value apna source dikhata hai aur submit se pehle edit ho sakta hai."},
    "doc_uploader": {
        "en": "Choose a PDF or image", "hi": "PDF या छवि चुनें", "hinglish": "PDF ya image chunein"},
    "doc_extract": {
        "en": "Extract from document", "hi": "दस्तावेज़ से निकालें", "hinglish": "Document se extract karein"},
    "doc_sample": {
        "en": "Try: sample marksheet (PDF)", "hi": "आज़माएँ: नमूना मार्कशीट (PDF)",
        "hinglish": "Try karein: sample marksheet (PDF)"},
    "doc_summary": {
        "en": "From **{source}** ({mode}): filled {fields}. Values above are editable — the same validators apply.",
        "hi": "**{source}** ({mode}) से: भरे गए {fields}। ऊपर दिए मूल्य संपादित किए जा सकते हैं — वही सत्यापन "
              "लागू होता है।",
        "hinglish": "**{source}** ({mode}) se: {fields} bhare gaye. Upar wali values editable hain — same "
                    "validators lagu hote hain."},
    "analyze": {
        "en": "Analyze request", "hi": "अनुरोध समझें", "hinglish": "Analyze request"},
    "analyze_spinner": {
        "en": "Understanding your request…", "hi": "आपका अनुरोध समझा जा रहा है…",
        "hinglish": "Aapka request samajha ja raha hai…"},
    "save": {
        "en": "Save & re-validate", "hi": "सहेजें और दोबारा जाँचें", "hinglish": "Save & re-validate karein"},
    "selected_service": {
        "en": "**Selected service:** {title} (local mock portal)",
        "hi": "**चयनित सेवा:** {title} (लोकल मॉक पोर्टल)",
        "hinglish": "**Selected service:** {title} (local mock portal)"},
    "field": {"en": "Field", "hi": "फ़ील्ड", "hinglish": "Field"},
    "value": {"en": "Value", "hi": "मूल्य", "hinglish": "Value"},
    "source": {"en": "Source", "hi": "स्रोत", "hinglish": "Source"},
    "status": {"en": "Status", "hi": "स्थिति", "hinglish": "Status"},
    "src_profile": {"en": "Profile", "hi": "प्रोफ़ाइल", "hinglish": "Profile"},
    "src_request": {"en": "Extracted from request", "hi": "अनुरोध से निकाला गया", "hinglish": "Request se nikala gaya"},
    "src_chat": {"en": "Chat answer", "hi": "चैट उत्तर", "hinglish": "Chat answer"},
    "status_invalid": {"en": "❌ Invalid", "hi": "❌ अमान्य", "hinglish": "❌ Invalid"},
    "status_missing": {"en": "⚠️ Missing", "hi": "⚠️ अनुपस्थित", "hinglish": "⚠️ Missing"},
    "status_ok": {"en": "✅ OK", "hi": "✅ ठीक", "hinglish": "✅ OK"},
    "missing_header": {
        "en": "Missing or invalid information", "hi": "अनुपस्थित या अमान्य जानकारी",
        "hinglish": "Missing ya invalid information"},
    "missing_warn": {
        "en": "**{field}** is required. Please provide it in the profile above, then click *Save & "
              "re-validate*. The agent will not guess it.",
        "hi": "**{field}** आवश्यक है। कृपया इसे ऊपर प्रोफ़ाइल में दें, फिर *सहेजें और दोबारा जाँचें* दबाएँ। "
              "एजेंट इसका अनुमान नहीं लगाएगा।",
        "hinglish": "**{field}** zaroori hai. Upar profile mein de dein, phir *Save & re-validate* dabayein. "
                    "Agent guess nahi karega."},
    "invalid_warn": {
        "en": "**{field}**: {msg}", "hi": "**{field}**: {msg}", "hinglish": "**{field}**: {msg}"},
    "all_valid": {
        "en": "All required information is present and valid.",
        "hi": "सभी आवश्यक जानकारी उपस्थित और मान्य है।",
        "hinglish": "Saari zaroori information maujood aur valid hai."},
    "prepare_hint": {
        "en": "When you're ready, authorize the agent to open the mock portal and fill the form. "
              "**Nothing is submitted at this step.**",
        "hi": "तैयार होने पर, एजेंट को मॉक पोर्टल खोलने और फ़ॉर्म भरने की अनुमति दें। **इस चरण में कुछ भी जमा "
              "नहीं होता।**",
        "hinglish": "Ready hone par agent ko mock portal kholne aur form bharne ki authorization dein. **Is "
                    "step par kuch bhi submit nahi hota.**"},
    "prepare": {
        "en": "Authorize agent to prepare the form", "hi": "एजेंट को फ़ॉर्म भरने की अनुमति दें",
        "hinglish": "Form prepare karne ke liye agent authorize karein"},
    "retry": {
        "en": "Retry preparation", "hi": "दोबारा तैयार करें", "hinglish": "Preparation retry karein"},
    "prepare_spinner": {
        "en": "Browser agent is working through the portal…",
        "hi": "ब्राउज़र एजेंट पोर्टल पर काम कर रहा है…",
        "hinglish": "Browser agent portal par kaam kar raha hai…"},
    "auto_header": {
        "en": "Browser automation status", "hi": "ब्राउज़र ऑटोमेशन स्थिति",
        "hinglish": "Browser automation status"},
    "fields_completed": {
        "en": "Fields completed", "hi": "पूर्ण फ़ील्ड", "hinglish": "Fields completed"},
    "completed": {"en": "Completed", "hi": "पूर्ण", "hinglish": "Completed"},
    "outstanding": {"en": "Outstanding", "hi": "शेष", "hinglish": "Outstanding"},
    "none": {"en": "none", "hi": "कोई नहीं", "hinglish": "koi nahi"},
    "portal_says": {
        "en": "Portal says **{field}**: {msg}", "hi": "पोर्टल का कहना है **{field}**: {msg}",
        "hinglish": "Portal bol raha hai **{field}**: {msg}"},
    "trace_title": {
        "en": "Agent activity trace (step-by-step gallery)",
        "hi": "एजेंट गतिविधि ट्रेस (चरण-दर-चरण गैलरी)",
        "hinglish": "Agent activity trace (step-by-step gallery)"},
    "trace_step": {
        "en": "**Step {step}** · page: `{page}` · planner: `{planner}`",
        "hi": "**चरण {step}** · पृष्ठ: `{page}` · प्लानर: `{planner}`",
        "hinglish": "**Step {step}** · page: `{page}` · planner: `{planner}`"},
    "trace_filled": {"en": "filled: {f}", "hi": "भरे गए: {f}", "hinglish": "filled: {f}"},
    "trace_action": {"en": "action: {a}", "hi": "क्रिया: {a}", "hinglish": "action: {a}"},
    "trace_note": {"en": "Note: {note}", "hi": "टिप्पणी: {note}", "hinglish": "Note: {note}"},
    "shot_caption": {
        "en": "Portal page at step {step}", "hi": "चरण {step} पर पोर्टल पृष्ठ",
        "hinglish": "Step {step} par portal page"},
    "trace_caption": {
        "en": "The agent only decides *where* to type or click. Values come from your validated profile, and "
              "it can never click the final submit button. Screenshots stay in this session's memory only and "
              "are never written to disk unless you download the audit report.",
        "hi": "एजेंट केवल यह तय करता है कि *कहाँ* टाइप या क्लिक करना है। मूल्य आपकी सत्यापित प्रोफ़ाइल से आते "
              "हैं, और वह कभी भी अंतिम सबमिट बटन पर क्लिक नहीं कर सकता। स्क्रीनशॉट केवल इस सत्र की मेमोरी में "
              "रहते हैं और ऑडिट रिपोर्ट डाउनलोड करने तक डिस्क पर कभी नहीं लिखे जाते।",
        "hinglish": "Agent sirf decide karta hai *kahan* type ya click karna hai. Values aapki validated profile "
                    "se aati hain, aur wo final submit button par kabhi click nahi kar sakta. Screenshots sirf "
                    "is session ki memory mein rehte hain, audit report download karne tak disk par nahi likhe "
                    "jaate."},
    "chat": {
        "en": "Chat with CivicPilot", "hi": "CivicPilot से बात करें", "hinglish": "CivicPilot se baat karein"},
    "chat_caption": {
        "en": "Answer here — one question at a time. The form above stays as a fallback. The agent never "
              "invents an answer for you.",
        "hi": "यहाँ उत्तर दें — एक बार में एक प्रश्न। ऊपर का फ़ॉर्म विकल्प बना रहेगा। एजेंट आपके लिए कभी उत्तर "
              "नहीं गढ़ता।",
        "hinglish": "Yahan jawab dein — ek baar mein ek sawaal. Upar wala form fallback bana rahega. Agent aapke "
                    "liye kabhi jawab nahi banata."},
    "chat_input": {
        "en": "Type your answer…", "hi": "अपना उत्तर लिखें…", "hinglish": "Apna jawab likhein…"},
    "chat_portal_err": {
        "en": " (the portal/form said: {err})", "hi": " (पोर्टल/फ़ॉर्म ने कहा: {err})",
        "hinglish": " (portal/form ne kaha: {err})"},
    "receipt_note": {
        "en": "Issued by the local MOCK portal. Fictional data only.",
        "hi": "लोकल मॉक पोर्टल द्वारा जारी। केवल काल्पनिक डेटा।",
        "hinglish": "Local MOCK portal ne issue kiya. Sirf fictional data."},
    "receipt_title": {
        "en": "CivicPilot receipt ({title})", "hi": "CivicPilot रसीद ({title})", "hinglish": "CivicPilot receipt ({title})"},
    "status_word": {"en": "Status", "hi": "स्थिति", "hinglish": "Status"},
    "setup_problem": {
        "en": "**Setup problem: {title}.** {detail}\n\n**Fix:** {fix}",
        "hi": "**सेटअप समस्या: {title}।** {detail}\n\n**समाधान:** {fix}",
        "hinglish": "**Setup problem: {title}.** {detail}\n\n**Fix:** {fix}"},
    "setup_recheck": {
        "en": "Re-check setup", "hi": "सेटअप दोबारा जाँचें", "hinglish": "Setup dobara check karein"},
    "setup_blocked": {
        "en": "Fix the setup problem shown at the top of the page first; the browser agent cannot run yet.",
        "hi": "पहले पेज के ऊपर दिखाई गई सेटअप समस्या ठीक करें; ब्राउज़र एजेंट अभी नहीं चल सकता।",
        "hinglish": "Pehle page ke upar dikhayi gayi setup problem fix karein; browser agent abhi nahi chal sakta."},
    "setup_spinner": {
        "en": "Checking setup (Playwright browser and mock portal)…",
        "hi": "सेटअप जाँचा जा रहा है (Playwright ब्राउज़र और मॉक पोर्टल)…",
        "hinglish": "Setup check ho raha hai (Playwright browser aur mock portal)…"},
}

STAGE_NAMES = {
    "en": ["Request Received", "Information Validated", "Form Prepared", "Awaiting Approval", "Submitted"],
    "hi": ["अनुरोध प्राप्त हुआ", "जानकारी सत्यापित", "फ़ॉर्म तैयार किया गया", "अनुमोदन की प्रतीक्षा", "जमा कर दिया गया"],
    "hinglish": ["Request Received", "Info Validated", "Form Prepared", "Approval Pending", "Submitted"],
}


def t(key: str, lang: str = "en", **fmt) -> str:
    """Translated string for `key`; falls back to English, then to the key itself."""
    entry = TRANSLATIONS.get(key) or {}
    text = entry.get(lang) or entry.get("en") or key
    return text.format(**fmt) if fmt else text


def stages(lang: str = "en") -> list:
    return STAGE_NAMES.get(lang) or STAGE_NAMES["en"]
