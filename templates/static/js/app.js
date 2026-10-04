const configuredApiBaseUrl = window.CAREERAI_CONFIG?.apiBaseUrl
    || document.querySelector('meta[name="careerai-api-base-url"]')?.content;
const API_BASE_URL = (configuredApiBaseUrl || (
    ['localhost', '127.0.0.1'].includes(window.location.hostname)
        ? `${window.location.protocol}//${window.location.hostname}:8000/api`
        : '/api'
)).replace(/\/$/, '');
const GOOGLE_CLIENT_ID = window.CAREERAI_CONFIG?.googleClientId
    || document.querySelector('meta[name="careerai-google-client-id"]')?.content
    || '';
let currentUserId = localStorage.getItem('user_id');
let currentPage = 1;

function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, (character) => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    }[character]));
}

function safeExternalUrl(value) {
    try {
        const url = new URL(value, window.location.origin);
        if (!['http:', 'https:'].includes(url.protocol)) return '#';
        return escapeHtml(url.href);
    } catch (error) {
        return '#';
    }
}

function encodeInlineValue(value) {
    return encodeURIComponent(String(value ?? ''));
}

function formatDate(value, includeTime = false) {
    if (!value) return 'Date unavailable';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return 'Date unavailable';
    return date.toLocaleString(undefined, includeTime
        ? { dateStyle: 'medium', timeStyle: 'short' }
        : { dateStyle: 'medium' });
}

window.onload = () => {
    const savedUsername = localStorage.getItem('username');
    if (currentUserId && savedUsername) {
        document.getElementById('loginBtn').classList.add('hidden');
        const profileControls = document.getElementById('userProfileControls');
        profileControls.classList.remove('hidden');
        profileControls.classList.add('flex');
        document.getElementById('loggedInUser').innerText = savedUsername;
        document.getElementById('tab-saved').classList.remove('hidden');
        document.getElementById('tab-history').classList.remove('hidden');

        // Dynamically fetch profile data
        fetchProfile();
    }

    fetchDynamicTypes();
};

// Preview will only show the most recently uploaded resume in the active session.
async function renderPDF(source) {
    document.getElementById('resumePlaceholder').classList.add('hidden');
    const canvasWrapper = document.getElementById('resumePreviewCanvasWrapper');
    if (!canvasWrapper) return;
    canvasWrapper.classList.remove('hidden');
    canvasWrapper.innerHTML = '<div class="text-white animate-pulse"><i class="fa-solid fa-spinner fa-spin mr-2"></i> Rendering PDF...</div>';

    try {
        pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.4.120/pdf.worker.min.js';

        let loadingTask;
        if (typeof source === 'string') {
            loadingTask = pdfjsLib.getDocument(source); // URL
        } else {
            loadingTask = pdfjsLib.getDocument({ data: source }); // ArrayBuffer
        }

        const pdf = await loadingTask.promise;
        canvasWrapper.innerHTML = '';

        for (let pageNum = 1; pageNum <= pdf.numPages; pageNum++) {
            const page = await pdf.getPage(pageNum);
            const containerWidth = document.getElementById('resumePreviewContainer').clientWidth || 400;
            const unscaledViewport = page.getViewport({ scale: 1.0 });
            const scale = (containerWidth - 40) / unscaledViewport.width;
            const viewport = page.getViewport({ scale: scale > 1.5 ? 1.5 : scale });

            const canvas = document.createElement('canvas');
            const context = canvas.getContext('2d');

            // Fix for blurry text on high DPI displays
            const outputScale = window.devicePixelRatio || 1;
            canvas.width = Math.floor(viewport.width * outputScale);
            canvas.height = Math.floor(viewport.height * outputScale);
            canvas.style.width = Math.floor(viewport.width) + "px";
            canvas.style.height = Math.floor(viewport.height) + "px";

            canvas.className = 'rounded-lg shadow-md bg-white mb-4';

            const transform = outputScale !== 1
                ? [outputScale, 0, 0, outputScale, 0, 0]
                : null;

            const renderContext = {
                canvasContext: context,
                transform: transform,
                viewport: viewport
            };
            await page.render(renderContext).promise;
            canvasWrapper.appendChild(canvas);
        }
    } catch (err) {
        console.error("Error rendering PDF", err);
        canvasWrapper.innerHTML = '<div class="text-rose-400">Failed to render PDF preview.</div>';
    }
}

async function fetchProfile() {
    try {
        const res = await fetch(`${API_BASE_URL}/profiles/`, {
            credentials: 'include'
        });
        if (res.ok) {
            const data = await res.json();
            const profiles = data.results || data;
            if (profiles.length > 0) {
                // Do not auto-populate the dashboard with historical data.
                // Just set the welcome banner with the user's name.
                document.getElementById('page-title').innerText = `Welcome, ${profiles[0].full_name || localStorage.getItem('username')}`;
                
                // Keep fetching recommendations for the Saved Matches tab
                fetchRecommendations();
            }
        } else if (res.status === 401 || res.status === 403) {
            console.warn("Session expired or unauthorized. Logging out locally.");
            // Clear local storage and UI manually without hitting the logout endpoint again to avoid loop
            currentUserId = null;
            localStorage.removeItem('user_id');
            localStorage.removeItem('username');
            localStorage.removeItem('saved_resume_pdf');
            document.getElementById('loginBtn').classList.remove('hidden');
            document.getElementById('tab-saved').classList.add('hidden');
            document.getElementById('tab-history').classList.add('hidden');
            const profileControls = document.getElementById('userProfileControls');
            profileControls.classList.add('hidden');
            profileControls.classList.remove('flex');
            document.getElementById('loggedInUser').innerText = "";
            switchTab('dashboard');
            showToast("Session expired. Please log in again.", "info");
        }
    } catch (e) {
        console.error("Error fetching profile", e);
    }
}

function populateDashboard(profile) {
    document.getElementById('page-title').innerText = `Welcome, ${profile.full_name || localStorage.getItem('username')}`;
    document.getElementById('targetRole').innerText = profile.target_role || "Not Set";
    document.getElementById('readinessScore').innerText = `${profile.readiness_score || 0}%`;

    // Skills Table
    const tbody = document.getElementById('skillsTableBody');
    tbody.innerHTML = '';

    if ((profile.current_skills && profile.current_skills.length > 0) || (profile.skill_gaps && profile.skill_gaps.length > 0)) {
        (profile.current_skills || []).forEach(skill => {
            tbody.innerHTML += `<tr><td class="py-4 px-6">${escapeHtml(skill)}</td><td class="py-4 px-6"><span class="px-2.5 py-1 text-xs rounded-full bg-emerald-100 text-emerald-700">Proficient</span></td><td class="py-4 px-6">Ready</td></tr>`;
        });
        (profile.skill_gaps || []).forEach(gap => {
            tbody.innerHTML += `
                        <tr>
                            <td class="py-4 px-6 font-medium text-gray-900">${escapeHtml(gap)}</td>
                            <td class="py-4 px-6"><span class="px-2.5 py-1 text-xs rounded-full bg-rose-100 text-rose-700">Missing</span></td>
                            <td class="py-4 px-6">
                                <button onclick="searchOpportunity('${encodeInlineValue(gap)}')" class="text-indigo-600 hover:text-indigo-800 font-semibold underline text-sm transition-colors">
                                    Find ${escapeHtml(gap)} Courses &rarr;
                                </button>
                            </td>
                        </tr>`;
        });
    } else {
        tbody.innerHTML = `<tr><td colspan="3" class="py-12 px-6 text-center text-slate-400 bg-slate-50/30"><i class="fa-solid fa-microchip text-4xl mb-4 text-slate-300 block"></i>Upload resume to view AI analysis</td></tr>`;
    }

    // Resume Builder
    const tipsList = document.getElementById('resumeTipsContainer');
    tipsList.innerHTML = '';

    if (profile.resume_improvements && profile.resume_improvements.length > 0) {
        profile.resume_improvements.forEach(tip => {
            tipsList.innerHTML += `<li class="p-4 bg-indigo-50 border-l-4 border-indigo-500 text-sm text-indigo-900 rounded-r-lg font-medium shadow-sm">${escapeHtml(tip)}</li>`;
        });
    } else {
        tipsList.innerHTML = `<li class="p-4 bg-gray-50 rounded-lg text-sm text-gray-700 border-l-4 border-indigo-500">Upload a resume to generate specific formatting and quantitative metric improvements.</li>`;
    }

    // Mock Interview
    const interviewContainer = document.getElementById('interviewQuestionsContainer');
    interviewContainer.innerHTML = '';
    if (profile.interview_questions && profile.interview_questions.length > 0) {
        (profile.interview_questions || []).forEach((q, idx) => {
            // Escape quotes so we can pass the string nicely to submitInterviewAnswer
            const encodedQ = encodeInlineValue(q);

            let savedFeedbackHtml = '';
            if (profile.interview_feedbacks && profile.interview_feedbacks[q]) {
                const savedData = profile.interview_feedbacks[q];
                let formattedFeedback = escapeHtml(savedData.feedback).replaceAll(/\n/g, '<br/>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
                savedFeedbackHtml = `
                    <div class="mt-4 p-4 rounded-xl text-sm font-medium leading-relaxed bg-emerald-50 text-emerald-800 border border-emerald-100">
                        <div class="mb-3 p-3 bg-white/50 rounded-lg italic text-gray-700"><strong>Your Answer:</strong> ${escapeHtml(savedData.answer)}</div>
                        <i class="fa-solid fa-square-poll-vertical text-emerald-600 text-lg mb-2"></i><br/>${formattedFeedback}
                    </div>
                `;
            }

            interviewContainer.innerHTML += `
                <div class="p-5 bg-white border border-gray-100 shadow-sm rounded-xl hover:shadow-md transition-shadow">
                    <span class="text-xs font-bold text-indigo-500 uppercase tracking-wider mb-2 block">Question ${idx + 1}</span>
                    <p class="text-sm font-semibold text-gray-800 mb-4">${escapeHtml(q)}</p>
                    ${savedFeedbackHtml ? savedFeedbackHtml : `
                    <div class="flex flex-col space-y-3">
                        <button id="btn-record-${idx}" onclick="toggleRecording(${idx})" class="w-fit bg-slate-50 hover:bg-rose-50 text-slate-600 hover:text-rose-600 border border-slate-200 hover:border-rose-200 px-4 py-2 rounded-lg text-xs font-bold transition-all flex items-center shadow-sm">
                            <i id="icon-record-${idx}" class="fa-solid fa-microphone mr-2"></i>
                            <span id="text-record-${idx}">Record Answer</span>
                        </button>
                        <div id="transcript-container-${idx}" class="bg-indigo-50/50 p-4 rounded-xl border border-indigo-100 relative">
                            <textarea id="transcript-${idx}" rows="3" placeholder="Type your answer here or click 'Record Answer' to use your microphone..." class="w-full text-sm text-slate-700 bg-white border border-indigo-200 rounded-lg p-3 mb-3 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none resize-y shadow-sm"></textarea>
                                <button onclick="submitInterviewAnswer(${idx}, '${encodedQ}')" class="bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold px-4 py-2 rounded-lg shadow-md transition-colors w-fit flex items-center">
                                <i class="fa-solid fa-robot mr-2"></i> Evaluate
                            </button>
                        </div>
                        <div id="feedback-container-${idx}" class="hidden p-4 rounded-xl text-sm font-medium leading-relaxed"></div>
                    </div>`}
                </div>`;
        });
    } else {
        interviewContainer.innerHTML = `<div class="p-4 bg-gray-50 rounded-lg text-sm text-gray-700 border-l-4 border-indigo-500">Upload your resume to formulate custom technical questions.</div>`;
    }
}

function searchOpportunity(query) {
    query = decodeURIComponent(query);
    switchTab('opportunities');
    document.getElementById('searchOpp').value = query;
    document.getElementById('typeOpp').value = "Course";
    fetchOpportunities();
}

async function fetchDynamicTypes() {
    try {
        const res = await fetch(`${API_BASE_URL}/opportunities/types/`);
        if (res.ok) {
            const types = await res.json();
            const typeSelect = document.getElementById('typeOpp');
            const savedTypeSelect = document.getElementById('savedTypeFilter');
            types.forEach(t => {
                const opt = document.createElement('option');
                opt.value = t;
                opt.textContent = t;
                typeSelect.appendChild(opt);

                if (savedTypeSelect) {
                    const optSaved = document.createElement('option');
                    optSaved.value = t;
                    optSaved.textContent = t;
                    savedTypeSelect.appendChild(optSaved);
                }
            });
        }
    } catch (e) {
        console.error("Error fetching opportunity types", e);
        showToast("Backend server is currently offline. Some features may not load.", "error");
    }
}

function showToast(message, type = 'success') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast-enter min-w-[300px] px-6 py-3 rounded-lg shadow-xl flex items-center justify-between pointer-events-auto border-l-4`;

    if (type === 'success') {
        toast.classList.add('bg-white', 'border-emerald-500', 'text-gray-800');
        toast.innerHTML = `<div class="flex items-center"><i class="fa-solid fa-circle-check text-emerald-500 mr-3 text-lg"></i><span class="font-medium">${message}</span></div>`;
    } else if (type === 'error') {
        toast.classList.add('bg-white', 'border-red-500', 'text-gray-800');
        toast.innerHTML = `<div class="flex items-center"><i class="fa-solid fa-circle-exclamation text-red-500 mr-3 text-lg"></i><span class="font-medium">${message}</span></div>`;
    } else {
        toast.classList.add('bg-gray-800', 'border-gray-600', 'text-white');
        toast.innerHTML = `<div class="flex items-center"><i class="fa-solid fa-bell text-gray-300 mr-3 text-lg"></i><span class="font-medium">${message}</span></div>`;
    }

    container.appendChild(toast);
    requestAnimationFrame(() => {
        toast.classList.remove('toast-enter');
        toast.classList.add('toast-enter-active');
    });

    setTimeout(() => {
        toast.classList.remove('toast-enter-active');
        toast.classList.add('toast-exit-active');
        setTimeout(() => toast.remove(), 900);
    }, 9000);
}

function switchTab(tabKey) {
    document.querySelectorAll('.content-view').forEach(el => el.classList.add('hidden'));
    document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active-tab'));

    document.getElementById(`section-${tabKey}`).classList.remove('hidden');
    document.getElementById(`tab-${tabKey}`).classList.add('active-tab');

    if (tabKey === 'opportunities') fetchOpportunities();
    if (tabKey === 'saved') fetchSavedOpportunities();
    if (tabKey === 'history') fetchResumeHistory();
}

function showLogin() {
    document.getElementById('loginModal').classList.remove('hidden');
}
function closeLogin() {
    document.getElementById('loginModal').classList.add('hidden');
}

async function socialLogin() {
    if (!GOOGLE_CLIENT_ID) {
        showToast("Google Login is not configured. Please use standard login for now.", "info");
        return;
    }

    if (!window.google?.accounts?.id) {
        showToast("Google Login is still loading. Please try again.", "error");
        return;
    }

    window.google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: handleGoogleCredential,
        cancel_on_tap_outside: true
    });
    window.google.accounts.id.prompt((notification) => {
        if (notification.isNotDisplayed() || notification.isSkippedMoment()) {
            showToast("Google Login could not open. Please try again or use standard login.", "error");
        }
    });
}

async function handleGoogleCredential(response) {
    if (!response?.credential) {
        showToast("Google did not return a valid credential.", "error");
        return;
    }

    try {
        const res = await fetch(`${API_BASE_URL}/social-login/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ token: response.credential })
        });
        const data = await res.json();
        if (!res.ok) {
            throw new Error(data.error || 'Google Login failed');
        }

        currentUserId = data.user_id;
        localStorage.setItem('user_id', data.user_id);
        localStorage.setItem('username', data.username || data.email || 'Student');
        document.getElementById('loginBtn').classList.add('hidden');
        document.getElementById('tab-saved').classList.remove('hidden');
        document.getElementById('tab-history').classList.remove('hidden');
        const profileControls = document.getElementById('userProfileControls');
        profileControls.classList.remove('hidden');
        profileControls.classList.add('flex');
        document.getElementById('loggedInUser').innerText = data.username || data.email || 'Student';
        closeLogin();
        showToast("Successfully logged in with Google!", "success");
        fetchProfile();
    } catch (error) {
        console.error('Google Login error:', error);
        showToast(error.message || "Error connecting to server", "error");
    }
}

async function standardLogin() {
    const username = document.getElementById('loginUsername').value;
    const password = document.getElementById('loginPassword').value;

    if (!username || !password) {
        showToast("Please enter username and password", "error");
        return;
    }

    try {
        const res = await fetch(`${API_BASE_URL}/login/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ username, password })
        });
        const data = await res.json();
        if (res.ok) {
            currentUserId = data.user_id;
            localStorage.setItem('user_id', data.user_id);
            localStorage.setItem('username', data.username);
            document.getElementById('loginBtn').classList.add('hidden');
            document.getElementById('tab-saved').classList.remove('hidden');
            document.getElementById('tab-history').classList.remove('hidden');
            const profileControls = document.getElementById('userProfileControls');
            profileControls.classList.remove('hidden');
            profileControls.classList.add('flex');
            document.getElementById('loggedInUser').innerText = data.username;
            closeLogin();
            showToast("Successfully logged in!", "success");
            fetchProfile();
        } else {
            showToast(data.error || "Login failed", "error");
        }
    } catch (e) {
        console.error(e);
        showToast("Error connecting to server", "error");
    }
}

function toggleAuth(mode) {
    const loginForm = document.getElementById('loginFormContainer');
    const registerForm = document.getElementById('registerFormContainer');
    const tabLogin = document.getElementById('tabLogin');
    const tabRegister = document.getElementById('tabRegister');

    if (mode === 'login') {
        loginForm.classList.remove('hidden');
        registerForm.classList.add('hidden');
        tabLogin.classList.add('border-indigo-600', 'text-indigo-600');
        tabLogin.classList.remove('border-transparent', 'text-gray-500');
        tabRegister.classList.remove('border-indigo-600', 'text-indigo-600');
        tabRegister.classList.add('border-transparent', 'text-gray-500');
    } else {
        loginForm.classList.add('hidden');
        registerForm.classList.remove('hidden');
        tabRegister.classList.add('border-indigo-600', 'text-indigo-600');
        tabRegister.classList.remove('border-transparent', 'text-gray-500');
        tabLogin.classList.remove('border-indigo-600', 'text-indigo-600');
        tabLogin.classList.add('border-transparent', 'text-gray-500');
    }
}

async function standardRegister() {
    const username = document.getElementById('registerUsername').value;
    const email = document.getElementById('registerEmail').value;
    const password = document.getElementById('registerPassword').value;

    if (!username || !password) {
        showToast("Please enter username and password", "error");
        return;
    }

    try {
        const res = await fetch(`${API_BASE_URL}/register/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ username, email, password })
        });
        const data = await res.json();
        if (res.ok) {
            currentUserId = data.user_id;
            localStorage.setItem('user_id', data.user_id);
            localStorage.setItem('username', data.username);
            document.getElementById('loginBtn').classList.add('hidden');
            document.getElementById('tab-saved').classList.remove('hidden');
            document.getElementById('tab-history').classList.remove('hidden');
            const profileControls = document.getElementById('userProfileControls');
            profileControls.classList.remove('hidden');
            profileControls.classList.add('flex');
            document.getElementById('loggedInUser').innerText = data.username;
            closeLogin();
            showToast("Account created successfully!", "success");
            fetchProfile();
        } else {
            showToast(data.error || "Registration failed", "error");
        }
    } catch (e) {
        console.error(e);
        showToast("Error connecting to server", "error");
    }
}

async function logout() {
    try {
        const res = await fetch(`${API_BASE_URL}/logout/`, {
            method: 'POST',
            credentials: 'include'
        });
        if (res.ok) {
            currentUserId = null;
            localStorage.removeItem('user_id');
            localStorage.removeItem('username');
            localStorage.removeItem('saved_resume_pdf');
            document.getElementById('loginBtn').classList.remove('hidden');
            document.getElementById('tab-saved').classList.add('hidden');
            document.getElementById('tab-history').classList.add('hidden');
            const profileControls = document.getElementById('userProfileControls');
            profileControls.classList.add('hidden');
            profileControls.classList.remove('flex');
            document.getElementById('loggedInUser').innerText = "";
            showToast("Successfully logged out!", "success");

            document.getElementById('page-title').innerText = "Welcome, Student";
            document.getElementById('targetRole').innerText = "N/A";
            document.getElementById('readinessScore').innerText = "--";
            document.getElementById('skillsTableBody').innerHTML = `<tr><td colspan="3" class="py-4 px-6 text-center text-gray-500">Upload resume to view analysis</td></tr>`;
            document.getElementById('schemesContainer').innerHTML = ``;
            document.getElementById('resumeTipsContainer').innerHTML = `<li class="p-4 bg-gray-50 rounded-lg text-sm text-gray-700 border-l-4 border-indigo-500">Upload a resume to generate specific formatting and quantitative metric improvements.</li>`;
            document.getElementById('interviewQuestionsContainer').innerHTML = `<p class="text-sm text-gray-400">Upload your resume to formulate custom technical questions.</p>`;
        }
    } catch (e) {
        console.error(e);
        showToast("Error during logout", "error");
    }
}

function toggleChat() {
    const chat = document.getElementById('chatWindow');
    chat.classList.toggle('hidden');
}

async function sendChat() {
    const input = document.getElementById('chatInput');
    const msg = input.value.trim();
    if (!msg) return;

    const history = document.getElementById('chatHistory');
    const userMessage = document.createElement('div');
    userMessage.className = 'bg-indigo-600 text-white p-3 rounded-lg w-3/4 ml-auto text-right shadow-md mb-3';
    userMessage.textContent = msg;
    history.appendChild(userMessage);
    input.value = '';
    history.scrollTop = history.scrollHeight;

    try {
        const res = await fetch(`${API_BASE_URL}/chatbot/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ message: msg })
        });
        const data = await res.json();
        const assistantMessage = document.createElement('div');
        assistantMessage.className = 'bg-white p-3 rounded-lg border border-gray-100 w-3/4 shadow-md mb-3 text-gray-800 leading-relaxed';
        assistantMessage.textContent = res.ok ? (data.response || 'No response received.') : (data.error || 'Unable to get a response.');
        history.appendChild(assistantMessage);
        history.scrollTop = history.scrollHeight;
    } catch (e) {
        history.innerHTML += `<div class="bg-red-50 text-red-500 p-3 rounded-lg border w-3/4 shadow-sm mb-3">Error fetching response.</div>`;
    }
}

async function uploadResume() {
    const input = document.getElementById('resumeInput');
    if (!input.files || input.files.length === 0) return;

    const btn = document.getElementById('uploadBtn');
    const originalText = btn.innerHTML;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i><span class="hidden md:inline">Analyzing...</span>`;
    btn.disabled = true;

    const formData = new FormData();
    formData.append('resume', input.files[0]);
    if (currentUserId) {
        formData.append('user_id', currentUserId);
    }

    const reader = new FileReader();
    reader.onload = async function (e) {
        const arrayBuffer = e.target.result;
        renderPDF(arrayBuffer);
    };
    reader.readAsArrayBuffer(input.files[0]);

    try {
        const response = await fetch(`${API_BASE_URL}/upload-resume/`, {
            method: 'POST',
            credentials: 'include',
            body: formData
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Failed to process resume.");

        showToast("Resume analyzed successfully!", "success");
        populateDashboard(data);
        fetchRecommendations();

    } catch (err) {
        console.error("Upload error:", err);
        showToast("Upload Exception: " + err.message, "error");
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

async function fetchOpportunities(page = 1) {
    currentPage = page;
    const search = document.getElementById('searchOpp').value;
    const type = document.getElementById('typeOpp').value;
    const sort = document.getElementById('sortOpp').value;

    let url = `${API_BASE_URL}/opportunities/?page=${page}&ordering=${sort}`;
    if (search) url += `&search=${encodeURIComponent(search)}`;
    if (type) url += `&type=${encodeURIComponent(type)}`;

    try {
        const res = await fetch(url, { credentials: 'include' });
        const data = await res.json();

        const container = document.getElementById('schemesContainer');
        container.innerHTML = '';

        let results = data.results || data;

        if (results.length === 0) {
            container.innerHTML = `<p class="text-sm text-gray-500 col-span-2 text-center py-8">No opportunities found for this query.</p>`;
            return;
        }

        results.forEach(opp => {
            container.innerHTML += `
                        <div class="bg-white p-6 md:p-8 rounded-3xl border border-gray-100 shadow-lg hover:shadow-xl flex flex-col justify-between transition-all duration-300 hover:-translate-y-1">
                            <div>
                                <div class="flex justify-between items-start mb-4">
                                    <span class="px-3 py-1 text-[10px] font-black uppercase tracking-wider rounded-full ${opp.is_free ? 'bg-emerald-100/50 text-emerald-700' : 'bg-amber-100/50 text-amber-700'}">${escapeHtml(opp.stipend_or_cost || 'Not specified')}</span>
                                    <span class="text-[10px] font-bold text-slate-400 uppercase tracking-widest">${escapeHtml(opp.opportunity_type || 'Opportunity')}</span>
                                </div>
                                <h4 class="text-xl font-extrabold text-slate-900 mb-2 leading-tight">${escapeHtml(opp.title || 'Untitled opportunity')}</h4>
                                <p class="text-xs text-indigo-500 font-bold mb-4 uppercase tracking-wide">${escapeHtml(opp.provider || 'Unknown provider')} &bull; ${escapeHtml(opp.mode || 'Not specified')} &bull; ${escapeHtml(opp.location || 'Not specified')}</p>
                                <p class="text-sm text-slate-500 font-medium mb-6 leading-relaxed">${escapeHtml((opp.description || '').substring(0, 120))}${opp.description && opp.description.length > 120 ? '...' : ''}</p>
                            </div>
                            <div class="pt-5 border-t border-slate-50 flex justify-between items-center relative z-10">
                                <button onclick="toggleBookmark(${opp.id}, this)" class="w-12 h-12 rounded-xl flex items-center justify-center transition-all duration-300 shadow-sm text-slate-400 bg-white border border-slate-200 hover:text-rose-500 hover:border-rose-200 hover:bg-rose-50">
                                    <i class="fa-regular fa-heart text-xl"></i>
                                </button>
                                ${['job', 'internship'].includes((opp.opportunity_type || '').toLowerCase()) ? 
                                    (opp.has_cover_letter ? 
                                        `<button onclick="generateCoverLetter(${opp.id})" class="ml-3 flex-1 bg-emerald-50 border border-emerald-200 hover:bg-emerald-100 text-emerald-700 text-sm font-bold px-3 py-3 rounded-xl transition-colors shadow-sm"><i class="fa-solid fa-file-lines mr-2"></i> View Cover Letter</button>` : 
                                        `<button onclick="generateCoverLetter(${opp.id})" class="ml-3 flex-1 bg-white border border-indigo-100 hover:bg-indigo-50 text-indigo-600 text-sm font-bold px-3 py-3 rounded-xl transition-colors shadow-sm"><i class="fa-solid fa-pen-nib mr-2"></i> Cover Letter</button>`
                                    ) : ''}
                                <a href="${safeExternalUrl(opp.url)}" target="_blank" rel="noopener noreferrer" class="flex-1 ml-3 text-center bg-gradient-to-r from-slate-800 to-slate-900 hover:from-indigo-600 hover:to-indigo-700 text-white text-sm font-bold px-4 py-3 rounded-xl transition-all duration-300 shadow-md hover:shadow-lg">${((opp.provider || '').toLowerCase().includes('youtube') || (opp.url || '').toLowerCase().includes('youtube')) ? 'View Now' : 'Apply Now'} &rarr;</a>
                            </div>
                        </div>
                    `;
        });

        const pag = document.getElementById('paginationControls');
        pag.innerHTML = '';
        if (data.previous) {
            pag.innerHTML += `<button onclick="fetchOpportunities(${page - 1})" class="px-4 py-2 bg-white border border-gray-200 rounded-lg shadow-sm hover:bg-gray-50 font-medium text-sm transition-colors">Previous</button>`;
        }
        if (data.next) {
            pag.innerHTML += `<button onclick="fetchOpportunities(${page + 1})" class="px-4 py-2 bg-white border border-gray-200 rounded-lg shadow-sm hover:bg-gray-50 font-medium text-sm transition-colors ml-2">Next</button>`;
        }
    } catch (e) {
        console.error("fetchOpportunities error:", e);
        document.getElementById('schemesContainer').innerHTML = `<p class="text-sm text-rose-500 bg-rose-50 p-6 rounded-2xl border border-rose-100 text-center col-span-full">Servers are currently offline or unavailable. Please try again later.</p>`;
        document.getElementById('paginationControls').innerHTML = '';
    }
}

async function fetchRecommendations() {
    try {
        const res = await fetch(`${API_BASE_URL}/recommendations/`, {
            credentials: 'include'
        });
        if (!res.ok) return;
        const data = await res.json();

        const allMatches = [...(data.schemes || []), ...(data.opportunities || [])];
        if (allMatches.length === 0) return;

        const container = document.getElementById('schemesContainer');
        let html = `<div class="col-span-full mb-2 flex items-center space-x-2"><i class="fa-solid fa-sparkles text-amber-500"></i><h4 class="text-sm font-bold text-indigo-700 uppercase tracking-wider">AI-Curated For Your Profile</h4></div>`;

        allMatches.slice(0, 6).forEach(match => {
            const opp = match.opportunity;
            const score = match.relevance_score;
            const scoreColor = score >= 70 ? 'emerald' : score >= 40 ? 'amber' : 'gray';
            html += `
                <div class="bg-white p-6 md:p-8 rounded-3xl border border-indigo-50 shadow-md flex flex-col justify-between hover:shadow-xl hover:border-indigo-100 transition-all duration-300 relative overflow-hidden hover:-translate-y-1">
                    <div class="absolute -right-4 -top-4 w-32 h-32 bg-gradient-to-br from-indigo-400 to-purple-400 rounded-full opacity-10 blur-2xl pointer-events-none"></div>
                    <div class="relative z-10">
                        <div class="flex justify-between items-start mb-4">
                            <span class="px-3 py-1 text-[10px] font-black rounded-full bg-${scoreColor}-100/80 text-${scoreColor}-700 shadow-sm uppercase tracking-widest"><i class="fa-solid fa-bolt mr-1"></i> Match: ${score}%</span>
                            <span class="text-[10px] font-bold text-slate-400 uppercase tracking-widest">${escapeHtml(opp.opportunity_type || 'Opportunity')}</span>
                        </div>
                        <h4 class="text-xl font-extrabold text-slate-900 mb-2 leading-tight">${escapeHtml(opp.title || 'Untitled opportunity')}</h4>
                        <p class="text-xs text-indigo-500 font-bold mb-4 uppercase tracking-wide">${escapeHtml(opp.provider || 'Unknown provider')} &bull; ${escapeHtml(opp.mode || 'Not specified')}</p>
                        <p class="text-sm text-slate-500 font-medium mb-4 leading-relaxed">${escapeHtml((opp.description || '').substring(0, 100))}${opp.description && opp.description.length > 100 ? '...' : ''}</p>
                        <div class="bg-indigo-50/50 p-4 rounded-2xl border border-indigo-50 mb-6">
                            <p class="text-xs text-indigo-700 italic font-semibold leading-relaxed">💡 ${escapeHtml(match.reasoning || 'No match explanation available.')}</p>
                        </div>
                    </div>
                    <div class="pt-5 border-t border-indigo-50 flex justify-between items-center relative z-10">
                        <button onclick="toggleBookmark(${opp.id}, this)" class="w-12 h-12 rounded-xl flex items-center justify-center transition-all duration-300 shadow-sm ${match.is_bookmarked ? 'text-rose-500 bg-rose-50 hover:bg-rose-100 border border-rose-100' : 'text-slate-400 bg-white border border-slate-200 hover:text-rose-500 hover:border-rose-200 hover:bg-rose-50'}">
                            <i class="${match.is_bookmarked ? 'fa-solid' : 'fa-regular'} fa-heart text-xl"></i>
                        </button>
                        ${['job', 'internship'].includes((opp.opportunity_type || '').toLowerCase()) ?
                    (match.cover_letter ?
                        `<button onclick="generateCoverLetter(${opp.id})" class="ml-3 flex-1 bg-emerald-50 border border-emerald-200 hover:bg-emerald-100 text-emerald-700 text-sm font-bold px-3 py-3 rounded-xl transition-colors shadow-sm"><i class="fa-solid fa-file-lines mr-2"></i> View Cover Letter</button>` :
                        `<button onclick="generateCoverLetter(${opp.id})" class="ml-3 flex-1 bg-white border border-indigo-100 hover:bg-indigo-50 text-indigo-600 text-sm font-bold px-3 py-3 rounded-xl transition-colors shadow-sm"><i class="fa-solid fa-pen-nib mr-2"></i> Cover Letter</button>`
                    ) : ''}
                        <a href="${safeExternalUrl(opp.url)}" target="_blank" rel="noopener noreferrer" class="flex-1 text-center bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white text-sm font-bold px-4 py-3 rounded-xl transition-all duration-300 shadow-md hover:shadow-lg ml-3">View &rarr;</a>
                    </div>
                </div>`;
        });

        container.innerHTML = html + container.innerHTML;
        showToast(`Found ${allMatches.length} AI-matched opportunities tailored for you!`, 'success');
    } catch (e) {
        console.error('fetchRecommendations error:', e);
        const container = document.getElementById('schemesContainer');
        if (container) {
            container.innerHTML = `<p class="text-sm text-rose-500 bg-rose-50 p-6 rounded-2xl border border-rose-100 text-center col-span-full">Servers are currently offline. Unable to load AI recommendations.</p>` + container.innerHTML;
        }
    }
}

async function fetchSavedOpportunities() {
    try {
        const res = await fetch(`${API_BASE_URL}/recommendations/`, {
            credentials: 'include'
        });
        if (!res.ok) return;
        const data = await res.json();
        let allMatches = [...(data.schemes || []), ...(data.opportunities || [])].filter(m => m.is_bookmarked);

        const filterValue = document.getElementById('savedTypeFilter')?.value;
        if (filterValue) {
            allMatches = allMatches.filter(m => m.opportunity.opportunity_type === filterValue);
        }

        const container = document.getElementById('savedContainer');
        container.innerHTML = '';

        if (allMatches.length === 0) {
            container.innerHTML = `<p class="text-sm text-gray-500 col-span-2 text-center py-8">No saved matches yet. Bookmark opportunities from the Dashboard to see them here.</p>`;
            return;
        }

        allMatches.forEach(match => {
            const opp = match.opportunity;
            container.innerHTML += `
                <div class="bg-white p-6 md:p-8 rounded-3xl border border-rose-50 shadow-md hover:shadow-xl flex flex-col justify-between transition-all duration-300 hover:-translate-y-1 relative overflow-hidden">
                    <div class="absolute -right-8 -top-8 w-32 h-32 bg-rose-400 rounded-full opacity-5 blur-2xl pointer-events-none"></div>
                    <div class="relative z-10">
                        <div class="flex justify-between items-start mb-4">
                            <span class="px-3 py-1 text-[10px] font-black uppercase tracking-wider rounded-full bg-emerald-100/50 text-emerald-700">${escapeHtml(opp.stipend_or_cost || 'Not specified')}</span>
                            <span class="text-[10px] font-bold text-slate-400 uppercase tracking-widest">${escapeHtml(opp.opportunity_type || 'Opportunity')}</span>
                        </div>
                        <h4 class="text-xl font-extrabold text-slate-900 mb-2 leading-tight">${escapeHtml(opp.title || 'Untitled opportunity')}</h4>
                        <p class="text-xs text-indigo-500 font-bold mb-4 uppercase tracking-wide">${escapeHtml(opp.provider || 'Unknown provider')}</p>
                        <p class="text-sm text-slate-500 font-medium mb-6 leading-relaxed">${escapeHtml((opp.description || '').substring(0, 120))}${opp.description && opp.description.length > 120 ? '...' : ''}</p>
                    </div>
                    <div class="pt-5 border-t border-slate-50 flex justify-between items-center relative z-10">
                        <button onclick="toggleBookmark(${opp.id}, this)" class="text-rose-500 hover:text-slate-400 text-sm font-bold px-3 py-3 transition-colors bg-rose-50 rounded-xl hover:bg-slate-50"><i class="fa-solid fa-heart mr-2"></i> Unsave</button>
                        ${['job', 'internship'].includes((opp.opportunity_type || '').toLowerCase()) ?
                    (match.cover_letter ?
                        `<button onclick="generateCoverLetter(${opp.id})" class="ml-3 flex-1 bg-emerald-50 border border-emerald-200 hover:bg-emerald-100 text-emerald-700 text-sm font-bold px-3 py-3 rounded-xl transition-colors shadow-sm"><i class="fa-solid fa-file-lines mr-2"></i> View Cover Letter</button>` :
                        `<button onclick="generateCoverLetter(${opp.id})" class="ml-3 flex-1 bg-white border border-indigo-100 hover:bg-indigo-50 text-indigo-600 text-sm font-bold px-3 py-3 rounded-xl transition-colors shadow-sm"><i class="fa-solid fa-pen-nib mr-2"></i> Cover Letter</button>`
                    ) : ''}
                        <a href="${safeExternalUrl(opp.url)}" target="_blank" rel="noopener noreferrer" class="flex-1 text-center bg-gradient-to-r from-slate-800 to-slate-900 hover:from-indigo-600 hover:to-indigo-700 text-white text-sm font-bold px-4 py-3 rounded-xl transition-all duration-300 shadow-md hover:shadow-lg ml-3">${((opp.provider || '').toLowerCase().includes('youtube') || (opp.url || '').toLowerCase().includes('youtube') || (opp.opportunity_type || '').toLowerCase().includes('course')) ? 'View Now' : 'Apply Now'} &rarr;</a>
                    </div>
                </div>
            `;
        });
    } catch (e) {
        console.error('fetchSavedOpportunities error:', e);
        document.getElementById('savedContainer').innerHTML = `<p class="text-sm text-rose-500 bg-rose-50 p-6 rounded-2xl border border-rose-100 text-center col-span-full">Servers are currently offline or unavailable. Please try again later.</p>`;
    }
}

async function fetchResumeHistory() {
    if (!currentUserId) {
        document.getElementById('historyContainer').innerHTML = `<p class="text-sm text-gray-500 bg-white p-6 rounded-2xl border border-gray-100 text-center">Please login to view your resume analysis history.</p>`;
        return;
    }
    try {
        const res = await fetch(`${API_BASE_URL}/resume-history/`, {
            credentials: 'include'
        });
        if (!res.ok) throw new Error('Failed to fetch history');
        const responseData = await res.json();
        const data = responseData.results || responseData;

        const container = document.getElementById('historyContainer');
        container.innerHTML = '';

        if (data.length === 0) {
            container.innerHTML = `<p class="text-sm text-gray-500 bg-white p-6 rounded-2xl border border-gray-100 text-center">No history found. Upload a resume to see your analysis timeline here.</p>`;
            return;
        }

        window.resumeAnalysisHistory = data;

        // Ensure container is a grid
        container.className = "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6";

        data.forEach((item, historyIdx) => {
            const date = formatDate(item.created_at, true);
            const scoreColor = item.readiness_score >= 70 ? 'text-emerald-500' : item.readiness_score >= 40 ? 'text-amber-500' : 'text-rose-500';

            // Generate a few skills badges for preview
            const previewSkillsHtml = (item.current_skills || []).slice(0, 3).map(s => `<span class="px-2 py-1 bg-indigo-50 text-indigo-600 text-xs rounded-md inline-block">${escapeHtml(s)}</span>`).join('');

            container.innerHTML += `
                <div class="bg-white p-6 rounded-2xl border border-indigo-100 shadow-sm hover:shadow-md transition-all flex flex-col h-full">
                    <div class="flex justify-between items-start mb-4">
                        <span class="text-xs font-bold text-indigo-600 bg-indigo-50 px-3 py-1 rounded-full"><i class="fa-solid fa-bullseye mr-1"></i> ${escapeHtml(item.target_role || 'General')}</span>
                        <span class="text-xs font-medium text-slate-400">${formatDate(item.created_at)}</span>
                    </div>
                    <div class="flex items-center justify-between mb-4">
                        <span class="text-3xl font-black ${scoreColor}">${item.readiness_score}%</span>
                        <span class="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Score</span>
                    </div>
                    <div class="mb-4 flex-grow">
                        <p class="text-xs text-slate-500 mb-2 font-medium">Top Skills Detected:</p>
                        <div class="flex flex-wrap items-center gap-2">
                            ${previewSkillsHtml || '<span class="text-xs text-slate-400">None detected</span>'}
                            ${(item.current_skills || []).length > 3 ? `<span class="text-xs font-bold text-indigo-400 ml-1">+${item.current_skills.length - 3} more</span>` : ''}
                        </div>
                    </div>
                    <button onclick="openAnalysisModal(${historyIdx})" class="w-full bg-indigo-50 hover:bg-indigo-100 text-indigo-700 text-sm font-bold py-3 rounded-xl transition-colors mt-auto flex items-center justify-center">
                        View Full Analysis <i class="fa-solid fa-arrow-right ml-2"></i>
                    </button>
                </div>
            `;
        });

        await fetchCoverLetterHistory();
    } catch (e) {
        console.error('fetchResumeHistory error:', e);
        const container = document.getElementById('historyContainer');
        container.className = "space-y-4";
        container.innerHTML = `<p class="text-sm text-red-500 bg-white p-6 rounded-2xl border border-red-100 text-center">Servers are currently offline or unavailable. Error loading history.</p>`;
    }
}

function openAnalysisModal(historyIdx) {
    if (!window.resumeAnalysisHistory || !window.resumeAnalysisHistory[historyIdx]) return;

    const item = window.resumeAnalysisHistory[historyIdx];
    const date = formatDate(item.created_at, true);
    const scoreColor = item.readiness_score >= 70 ? 'text-emerald-500' : item.readiness_score >= 40 ? 'text-amber-500' : 'text-rose-500';

    // Generate skills badges (All, not sliced)
    const currentSkillsHtml = (item.current_skills || []).map(s => `<span class="px-2 py-1 bg-indigo-50 text-indigo-600 text-xs rounded-md mr-2 mb-2 inline-block">${escapeHtml(s)}</span>`).join('');
    const gapSkillsHtml = (item.skill_gaps || []).map(s => `<span class="px-2 py-1 bg-rose-50 text-rose-600 text-xs rounded-md mr-2 mb-2 inline-block">${escapeHtml(s)}</span>`).join('');

    // Skill Gap Analysis Table
    let skillGapTableRows = '';
    (item.skill_gaps || []).forEach(gap => {
        skillGapTableRows += `
            <tr>
                <td class="py-4 px-6 font-medium text-gray-900">${escapeHtml(gap)}</td>
                <td class="py-4 px-6"><span class="px-2.5 py-1 text-xs rounded-full bg-rose-100 text-rose-700">Missing</span></td>
                <td class="py-4 px-6">
                    <button onclick="searchOpportunity('${encodeInlineValue(gap)}'); closeAnalysisModal();" class="text-indigo-600 hover:text-indigo-800 font-semibold underline text-sm transition-colors">
                        Find ${escapeHtml(gap)} Courses &rarr;
                    </button>
                </td>
            </tr>`;
    });
    const skillGapSection = skillGapTableRows ? `
        <div class="mt-8 pt-6 border-t border-gray-100">
            <h5 class="text-lg font-bold text-slate-900 mb-4 flex items-center"><div class="bg-blue-50 text-blue-600 p-1.5 rounded-lg mr-3 text-sm"><i class="fa-solid fa-chart-line"></i></div> Skill Gap Analysis</h5>
            <div class="overflow-x-auto">
                <table class="w-full text-left text-sm text-gray-600">
                    <thead class="bg-gray-50 text-gray-700 uppercase text-[10px] tracking-wider font-bold">
                        <tr>
                            <th class="py-3 px-6 rounded-tl-lg">Skill Requirement</th>
                            <th class="py-3 px-6">Level</th>
                            <th class="py-3 px-6 rounded-tr-lg">Recommendation</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-50">
                        ${skillGapTableRows}
                    </tbody>
                </table>
            </div>
        </div>
    ` : '';

    // Resume Improvements List
    let improvementsHtml = '';
    (item.resume_improvements || []).forEach(tip => {
        improvementsHtml += `<li class="p-4 bg-indigo-50 border-l-4 border-indigo-500 text-sm text-indigo-900 rounded-r-lg font-medium shadow-sm mb-2">${escapeHtml(tip)}</li>`;
    });
    const improvementsSection = improvementsHtml ? `
        <div class="mt-8 pt-6 border-t border-gray-100">
            <h5 class="text-lg font-bold text-slate-900 mb-4">Resume Presentation Optimizations</h5>
            <ul class="space-y-3">
                ${improvementsHtml}
            </ul>
        </div>
    ` : '';

    // Mock Interview Questions
    let interviewHtml = '';
    (item.interview_questions || []).forEach((q, idx) => {
        const encodedQ = encodeInlineValue(q);
        const uId = `hist-${historyIdx}-${idx}`; // Unique ID across all history elements

        let savedFeedbackHtml = '';
        if (item.interview_feedbacks && item.interview_feedbacks[q]) {
            const savedData = item.interview_feedbacks[q];
            let formattedFeedback = escapeHtml(savedData.feedback).replaceAll(/\n/g, '<br/>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
            savedFeedbackHtml = `
                <div class="mt-4 p-4 rounded-xl text-sm font-medium leading-relaxed bg-emerald-50 text-emerald-800 border border-emerald-100">
                    <div class="mb-3 p-3 bg-white/50 rounded-lg italic text-gray-700"><strong>Your Answer:</strong> ${escapeHtml(savedData.answer)}</div>
                    <i class="fa-solid fa-square-poll-vertical text-emerald-600 text-lg mb-2"></i><br/>${formattedFeedback}
                </div>
            `;
        }

        interviewHtml += `
            <div class="p-5 bg-white border border-gray-100 shadow-sm rounded-xl hover:shadow-md transition-shadow mb-4">
                <span class="text-xs font-bold text-indigo-500 uppercase tracking-wider mb-2 block">Question ${idx + 1}</span>
                <p class="text-sm font-semibold text-gray-800 mb-4">${escapeHtml(q)}</p>
                ${savedFeedbackHtml ? savedFeedbackHtml : `
                <div class="flex flex-col space-y-3">
                    <button id="btn-record-${uId}" onclick="toggleRecording('${uId}')" class="w-fit bg-slate-50 hover:bg-rose-50 text-slate-600 hover:text-rose-600 border border-slate-200 hover:border-rose-200 px-4 py-2 rounded-lg text-xs font-bold transition-all flex items-center shadow-sm">
                        <i id="icon-record-${uId}" class="fa-solid fa-microphone mr-2"></i> 
                        <span id="text-record-${uId}">Record Answer</span>
                    </button>
                    <div id="transcript-container-${uId}" class="bg-indigo-50/50 p-4 rounded-xl border border-indigo-100 relative">
                        <textarea id="transcript-${uId}" rows="3" placeholder="Type your answer here or click 'Record Answer' to use your microphone..." class="w-full text-sm text-slate-700 bg-white border border-indigo-200 rounded-lg p-3 mb-3 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none resize-y shadow-sm"></textarea>
                        <button onclick="submitInterviewAnswer('${uId}', '${encodedQ}', ${item.id})" class="bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold px-4 py-2 rounded-lg shadow-md transition-colors w-fit flex items-center">
                            <i class="fa-solid fa-robot mr-2"></i> Evaluate
                        </button>
                    </div>
                    <div id="feedback-container-${uId}" class="hidden p-4 rounded-xl text-sm font-medium leading-relaxed"></div>
                </div>`}
            </div>`;
    });
    const interviewSection = interviewHtml ? `
        <div class="mt-8 pt-6 border-t border-gray-100">
            <h5 class="text-lg font-bold text-slate-900 mb-4">Tailored Mock Interview Questions</h5>
            <div>${interviewHtml}</div>
        </div>
    ` : '';

    const contentHtml = `
        <div class="flex flex-col md:flex-row justify-between items-start mb-6 border-b border-gray-50 pb-6">
            <div>
                <h4 class="text-2xl font-extrabold text-slate-900">${escapeHtml(item.target_role || 'Target Role Not Set')}</h4>
                <p class="text-sm text-slate-500 mt-2"><i class="fa-regular fa-calendar mr-2"></i> Analyzed on: ${date}</p>
            </div>
            <div class="flex flex-col items-end mt-4 md:mt-0">
                <span class="text-4xl font-black ${scoreColor}">${item.readiness_score}%</span>
                <span class="text-xs font-bold text-slate-400 uppercase tracking-widest mt-1">Score</span>
            </div>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div>
                <h5 class="text-sm font-bold text-slate-700 mb-3"><i class="fa-solid fa-check text-emerald-500 mr-2"></i> Current Skills</h5>
                <div class="flex flex-wrap">${currentSkillsHtml || '<span class="text-sm text-slate-400">None detected</span>'}</div>
            </div>
            <div>
                <h5 class="text-sm font-bold text-slate-700 mb-3"><i class="fa-solid fa-xmark text-rose-500 mr-2"></i> Skill Gaps</h5>
                <div class="flex flex-wrap">${gapSkillsHtml || '<span class="text-sm text-slate-400">None detected</span>'}</div>
            </div>
        </div>
        
        ${improvementsSection}
        ${skillGapSection}
        ${interviewSection}

        ${item.resume_file ? `
        <div class="mt-8 pt-6 border-t border-gray-50 flex justify-between items-center">
            <span class="text-sm font-bold text-slate-500 uppercase tracking-widest"><i class="fa-solid fa-paperclip mr-2"></i> Original Document</span>
            <a href="${safeExternalUrl(item.resume_file)}" target="_blank" rel="noopener noreferrer" class="text-sm font-bold text-indigo-600 hover:text-indigo-800 bg-indigo-50 hover:bg-indigo-100 px-4 py-2 rounded-lg transition-colors flex items-center shadow-sm">
                View PDF <i class="fa-solid fa-arrow-up-right-from-square ml-2"></i>
            </a>
        </div>` : ''}
    `;

    document.getElementById('analysisModalContent').innerHTML = contentHtml;
    document.getElementById('analysisModal').classList.remove('hidden');
}

function closeAnalysisModal() {
    document.getElementById('analysisModal').classList.add('hidden');
}

async function fetchCoverLetterHistory() {
    try {
        const res = await fetch(`${API_BASE_URL}/cover-letter-history/`, {
            credentials: 'include'
        });
        if (!res.ok) throw new Error('Failed to fetch cover letter history');
        const responseData = await res.json();
        const data = responseData.results || responseData;

        const container = document.getElementById('coverLetterHistoryContainer');
        container.innerHTML = '';

        if (data.length === 0) {
            container.innerHTML = `<p class="text-sm text-gray-500 bg-white p-6 rounded-2xl border border-gray-100 text-center col-span-full">No cover letters found. Generate one for a job to see it here.</p>`;
            return;
        }

        data.forEach(match => {
            const opp = match.opportunity;
            const date = formatDate(match.created_at, true);
            container.innerHTML += `
                <div class="bg-white p-6 rounded-2xl border border-emerald-100 shadow-sm hover:shadow-md transition-all">
                    <div class="flex justify-between items-start mb-4">
                        <span class="text-xs font-bold text-emerald-600 bg-emerald-50 px-3 py-1 rounded-full"><i class="fa-solid fa-file-contract mr-1"></i> Cover Letter</span>
                        <span class="text-xs font-medium text-slate-400">${date}</span>
                    </div>
                    <h4 class="text-lg font-bold text-slate-900 mb-1">${escapeHtml(opp.title)}</h4>
                    <p class="text-xs font-semibold text-indigo-500 uppercase tracking-wide mb-4">${escapeHtml(opp.provider)}</p>
                    <div class="bg-slate-50 p-4 rounded-xl text-sm text-slate-600 mb-4 line-clamp-3 h-24 overflow-hidden relative">
                        <div class="absolute bottom-0 left-0 right-0 h-10 bg-gradient-to-t from-slate-50 to-transparent"></div>
                        ${escapeHtml(match.cover_letter)}
                    </div>
                    <button onclick="generateCoverLetter(${opp.id})" class="w-full bg-emerald-50 hover:bg-emerald-100 text-emerald-700 text-sm font-bold py-3 rounded-xl transition-colors">
                        Read Full Letter &rarr;
                    </button>
                </div>
            `;
        });
    } catch (e) {
        console.error('fetchCoverLetterHistory error:', e);
        document.getElementById('coverLetterHistoryContainer').innerHTML = `<p class="text-sm text-red-500 bg-white p-6 rounded-2xl border border-red-100 text-center col-span-full">Servers are currently offline or unavailable. Error loading cover letters.</p>`;
    }
}

async function toggleBookmark(oppId, btnElement) {
    if (!currentUserId) {
        showToast('Please login to save opportunities', 'error');
        return;
    }

    // Optimistic UI update
    const icon = btnElement.querySelector('i');
    const isCurrentlySaved = icon.classList.contains('fa-solid');

    if (isCurrentlySaved) {
        icon.classList.remove('fa-solid');
        icon.classList.add('fa-regular');
        btnElement.classList.replace('text-rose-500', 'text-gray-400');
        btnElement.classList.replace('bg-rose-50', 'bg-gray-50');
        btnElement.classList.replace('hover:bg-rose-100', 'hover:bg-rose-50');
        btnElement.classList.replace('hover:text-rose-500', 'hover:text-rose-500');
    } else {
        icon.classList.remove('fa-regular');
        icon.classList.add('fa-solid');
        btnElement.classList.replace('text-gray-400', 'text-rose-500');
        btnElement.classList.replace('bg-gray-50', 'bg-rose-50');
        btnElement.classList.replace('hover:bg-rose-50', 'hover:bg-rose-100');
    }

    try {
        const res = await fetch(`${API_BASE_URL}/bookmark/${oppId}/`, {
            method: 'POST',
            credentials: 'include'
        });
        if (!res.ok) throw new Error('Failed to toggle bookmark');

        if (isCurrentlySaved) {
            showToast('Opportunity removed from saved matches.', 'info');
        } else {
            showToast('Opportunity saved successfully!', 'success');
        }

        // If we are on the saved tab, re-fetch to update list
        if (document.getElementById('section-saved').classList.contains('hidden') === false) {
            fetchSavedOpportunities();
        }
    } catch (e) {
        console.error(e);
        showToast('Failed to sync bookmark. Please try again.', 'error');
        icon.classList.toggle('fa-solid', isCurrentlySaved);
        icon.classList.toggle('fa-regular', !isCurrentlySaved);
        btnElement.classList.toggle('text-rose-500', isCurrentlySaved);
        btnElement.classList.toggle('text-gray-400', !isCurrentlySaved);
        btnElement.classList.toggle('bg-rose-50', isCurrentlySaved);
        btnElement.classList.toggle('bg-gray-50', !isCurrentlySaved);
    }
}

async function generateCoverLetter(oppId) {
    if (!currentUserId) {
        showToast('Please login to generate cover letters', 'error');
        return;
    }

    const modal = document.getElementById('coverLetterModal');
    const content = document.getElementById('coverLetterContent');
    modal.classList.remove('hidden');
    content.innerHTML = `<div class="flex flex-col items-center justify-center h-full text-indigo-500"><i class="fa-solid fa-spinner fa-spin text-3xl mb-3"></i><p>CareerAI is writing your personalized cover letter...</p></div>`;

    try {
        const res = await fetch(`${API_BASE_URL}/cover-letter/${oppId}/`, {
            method: 'POST',
            credentials: 'include'
        });
        const data = await res.json();

        if (res.ok) {
            content.innerText = data.cover_letter;
            // Update button state visually
            const buttons = document.querySelectorAll(`button[onclick="generateCoverLetter(${oppId})"]`);
            buttons.forEach(btn => {
                if (btn.innerText.includes('Cover Letter') && !btn.innerText.includes('View Cover Letter')) {
                    btn.className = "ml-3 flex-1 bg-emerald-50 border border-emerald-200 hover:bg-emerald-100 text-emerald-700 text-sm font-bold px-3 py-3 rounded-xl transition-colors shadow-sm";
                    btn.innerHTML = `<i class="fa-solid fa-file-lines mr-2"></i> View Cover Letter`;
                }
            });
        } else {
            content.innerHTML = `<div class="text-rose-500 text-center"><i class="fa-solid fa-triangle-exclamation mb-2 text-2xl"></i><p>${escapeHtml(data.error || 'Failed to generate cover letter.')}</p></div>`;
        }
    } catch (e) {
        console.error(e);
        content.innerHTML = `<div class="text-rose-500 text-center"><i class="fa-solid fa-wifi mb-2 text-2xl"></i><p>Network error connecting to AI service.</p></div>`;
    }
}

function closeCoverLetterModal() {
    document.getElementById('coverLetterModal').classList.add('hidden');
}

function copyCoverLetter() {
    const text = document.getElementById('coverLetterContent').innerText;
    if (text) {
        navigator.clipboard.writeText(text).then(() => {
            showToast('Cover letter copied to clipboard!', 'success');
        });
    }
}

// Google Translate Integration
function googleTranslateElementInit() {
    new google.translate.TranslateElement({
        pageLanguage: 'en',
        includedLanguages: 'hi,en',
        autoDisplay: false
    }, 'google_translate_element');

    // Use MutationObserver to instantly fix Lighthouse Accessibility audits 
    // the moment Google's script injects the select element.
    const observer = new MutationObserver((mutations, obs) => {
        const selectField = document.querySelector(".goog-te-combo");
        if (selectField) {
            if (!selectField.id) selectField.id = "google_translate_select";
            if (!selectField.name) selectField.name = "google_translate_select";
            if (!selectField.getAttribute("aria-label")) selectField.setAttribute("aria-label", "Language Translate Widget");
            obs.disconnect(); // Stop observing once fixed
        }
    });
    observer.observe(document.getElementById('google_translate_element'), { childList: true, subtree: true });
}

function changeLanguage(langCode) {
    const selectField = document.querySelector(".goog-te-combo");
    if (selectField) {
        selectField.value = langCode;
        // Fix for the double-click bug: use bubbles: true so Google's listener catches it
        selectField.dispatchEvent(new Event('change', { bubbles: true, cancelable: true }));

        // Update UI toggle
        if (langCode === 'en') {
            document.getElementById('lang-en').classList.add('bg-white', 'shadow-sm', 'text-indigo-600');
            document.getElementById('lang-en').classList.remove('text-slate-500', 'hover:text-slate-700');
            document.getElementById('lang-hi').classList.add('text-slate-500', 'hover:text-slate-700');
            document.getElementById('lang-hi').classList.remove('bg-white', 'shadow-sm', 'text-indigo-600');
        } else {
            document.getElementById('lang-hi').classList.add('bg-white', 'shadow-sm', 'text-indigo-600');
            document.getElementById('lang-hi').classList.remove('text-slate-500', 'hover:text-slate-700');
            document.getElementById('lang-en').classList.add('text-slate-500', 'hover:text-slate-700');
            document.getElementById('lang-en').classList.remove('bg-white', 'shadow-sm', 'text-indigo-600');
        }
    }
}

// Password Visibility Toggle
function togglePasswordVisibility(inputId, iconId) {
    const input = document.getElementById(inputId);
    const icon = document.getElementById(iconId);

    if (input.type === "password") {
        input.type = "text";
        icon.classList.remove("fa-eye");
        icon.classList.add("fa-eye-slash");
    } else {
        input.type = "password";
        icon.classList.remove("fa-eye-slash");
        icon.classList.add("fa-eye");
    }
}

// Mock Interview Audio Recording (Web Speech API)
let recognition = null;
let isRecording = false;
let currentRecordingIdx = -1;

if ('webkitSpeechRecognition' in window) {
    recognition = new webkitSpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US';

    recognition.onresult = (event) => {
        if (currentRecordingIdx !== -1) {
            const transcriptEl = document.getElementById(`transcript-${currentRecordingIdx}`);
            let total = "";
            for (let i = 0; i < event.results.length; i++) {
                total += event.results[i][0].transcript;
            }
            transcriptEl.value = total;
        }
    };

    recognition.onerror = (e) => {
        console.error("Speech Recognition Error:", e);
        showToast("Microphone error. Please allow microphone permissions.", "error");
        stopRecording();
    };

    recognition.onend = () => {
        if (isRecording) {
            stopRecording();
        }
    };
}

function toggleRecording(idx) {
    if (!recognition) {
        showToast("Your browser does not support voice recording (Try Chrome).", "error");
        return;
    }

    if (isRecording) {
        if (currentRecordingIdx === idx) {
            stopRecording();
        } else {
            stopRecording();
            setTimeout(() => startRecording(idx), 200); // slight delay to allow stop
        }
    } else {
        startRecording(idx);
    }
}

function startRecording(idx) {
    currentRecordingIdx = idx;
    isRecording = true;

    const icon = document.getElementById(`icon-record-${idx}`);
    const text = document.getElementById(`text-record-${idx}`);
    const btn = document.getElementById(`btn-record-${idx}`);

    btn.classList.add('bg-rose-100', 'text-rose-600', 'border-rose-300', 'animate-pulse');
    icon.classList.remove('fa-microphone');
    icon.classList.add('fa-stop');
    text.innerText = "Stop Recording";

    const transcriptEl = document.getElementById(`transcript-${idx}`);
    if (transcriptEl.value === "") {
        transcriptEl.placeholder = "Listening... Speak your answer.";
    }
    document.getElementById(`feedback-container-${idx}`).classList.add('hidden');
    document.getElementById(`feedback-container-${idx}`).classList.remove('bg-emerald-50', 'text-emerald-800', 'border', 'border-emerald-100', 'bg-rose-50', 'text-rose-800');

    try {
        recognition.start();
    } catch (e) { }
}

function stopRecording() {
    if (currentRecordingIdx === -1) return;
    const idx = currentRecordingIdx;
    isRecording = false;
    currentRecordingIdx = -1;

    const icon = document.getElementById(`icon-record-${idx}`);
    const text = document.getElementById(`text-record-${idx}`);
    const btn = document.getElementById(`btn-record-${idx}`);

    btn.classList.remove('bg-rose-100', 'text-rose-600', 'border-rose-300', 'animate-pulse');
    icon.classList.remove('fa-stop');
    icon.classList.add('fa-microphone');
    text.innerText = "Record Answer";

    try {
        recognition.stop();
    } catch (e) { }

    const transcriptEl = document.getElementById(`transcript-${idx}`);
    if (transcriptEl) {
        transcriptEl.placeholder = "Type your answer here or click 'Record Answer' to use your microphone...";
    }
}

async function submitInterviewAnswer(idx, question, analysisId = null) {
    if (isRecording) stopRecording();

    question = decodeURIComponent(question);

    const answer = document.getElementById(`transcript-${idx}`).value.trim();
    if (!answer || answer.includes("Listening...")) {
        showToast("Please record a valid answer first.", "error");
        return;
    }

    const feedbackContainer = document.getElementById(`feedback-container-${idx}`);
    feedbackContainer.classList.remove('hidden');
    feedbackContainer.innerHTML = `<i class="fa-solid fa-spinner fa-spin text-indigo-500 mr-2"></i> Analyzing your response...`;

    try {
        const payload = { question, answer };
        if (analysisId) payload.analysis_id = analysisId;

        const res = await fetch(`${API_BASE_URL}/interview-evaluate/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(payload)
        });
        const data = await res.json();

        if (res.ok) {
            feedbackContainer.classList.add('bg-emerald-50', 'text-emerald-800', 'border', 'border-emerald-100');
            // Bold the specific keywords Gemini tends to use (Rating, Good, Missing)
            let formattedFeedback = escapeHtml(data.feedback || 'No feedback received.').replace(/\n/g, '<br/>');
            formattedFeedback = formattedFeedback.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
            feedbackContainer.innerHTML = `<i class="fa-solid fa-square-poll-vertical text-emerald-600 text-lg mb-2"></i><br/>${formattedFeedback}`;
        } else {
            feedbackContainer.classList.add('bg-rose-50', 'text-rose-800');
            feedbackContainer.innerHTML = `<i class="fa-solid fa-triangle-exclamation"></i> ${escapeHtml(data.error || 'Unable to evaluate answer.')}`;
        }
    } catch (e) {
        console.error(e);
        feedbackContainer.classList.add('bg-rose-50', 'text-rose-800');
        feedbackContainer.innerHTML = `Network error connecting to AI.`;
    }
}