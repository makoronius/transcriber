// Theme Management
function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return null;
}

function setCookie(name, value, days = 365) {
    const date = new Date();
    date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
    const expires = `expires=${date.toUTCString()}`;
    document.cookie = `${name}=${value};${expires};path=/`;
}

function initTheme() {
    // Get saved theme from cookie or default to 'dark'
    const savedTheme = getCookie('theme') || 'dark';
    applyTheme(savedTheme);

    // Update button states
    updateThemeButtons(savedTheme);
}

function applyTheme(theme) {
    const body = document.body;

    if (theme === 'auto') {
        // Use system preference
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        if (prefersDark) {
            body.classList.remove('light-theme');
        } else {
            body.classList.add('light-theme');
        }
    } else if (theme === 'light') {
        body.classList.add('light-theme');
    } else {
        body.classList.remove('light-theme');
    }
}

function updateThemeButtons(activeTheme) {
    document.querySelectorAll('.theme-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.theme === activeTheme) {
            btn.classList.add('active');
        }
    });
}

function switchTheme(theme) {
    setCookie('theme', theme);
    applyTheme(theme);
    updateThemeButtons(theme);
}

// Modal Management System
const ModalManager = {
    activeModals: [],
    focusableSelectors: 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',

    open(modalElement) {
        if (!modalElement) return;

        // Add to stack
        this.activeModals.push(modalElement);

        // Lock body scroll
        document.body.style.overflow = 'hidden';

        // Set ARIA attributes
        modalElement.setAttribute('role', 'dialog');
        modalElement.setAttribute('aria-modal', 'true');

        // Show modal
        modalElement.classList.add('show');

        // Store previously focused element
        modalElement._previouslyFocused = document.activeElement;

        // Set initial focus to first focusable element or close button
        setTimeout(() => {
            const focusable = this.getFocusableElements(modalElement);
            if (focusable.length > 0) {
                focusable[0].focus();
            }
        }, 100);

        // Add event listeners
        modalElement._keydownHandler = this.handleKeyDown.bind(this, modalElement);
        modalElement._clickHandler = this.handleBackdropClick.bind(this, modalElement);

        document.addEventListener('keydown', modalElement._keydownHandler);
        modalElement.addEventListener('click', modalElement._clickHandler);

        // Disable background interaction
        this.disableBackground();
    },

    close(modalElement) {
        if (!modalElement) return;

        // Remove from stack
        const index = this.activeModals.indexOf(modalElement);
        if (index > -1) {
            this.activeModals.splice(index, 1);
        }

        // Remove event listeners
        if (modalElement._keydownHandler) {
            document.removeEventListener('keydown', modalElement._keydownHandler);
        }
        if (modalElement._clickHandler) {
            modalElement.removeEventListener('click', modalElement._clickHandler);
        }

        // Hide modal
        modalElement.classList.remove('show');

        // Restore focus to previously focused element
        if (modalElement._previouslyFocused && modalElement._previouslyFocused.focus) {
            modalElement._previouslyFocused.focus();
        }

        // Unlock body scroll if no modals are active
        if (this.activeModals.length === 0) {
            document.body.style.overflow = '';
            this.enableBackground();
        }
    },

    handleKeyDown(modalElement, e) {
        // Escape key closes modal
        if (e.key === 'Escape') {
            e.preventDefault();
            e.stopPropagation();

            // Special handling for confirm modal
            if (modalElement.id === 'confirmModal' && typeof closeConfirmModal === 'function') {
                closeConfirmModal(false);
            } else {
                this.close(modalElement);
            }
            return;
        }

        // Tab key - trap focus within modal
        if (e.key === 'Tab') {
            const focusable = this.getFocusableElements(modalElement);
            if (focusable.length === 0) return;

            const firstFocusable = focusable[0];
            const lastFocusable = focusable[focusable.length - 1];

            if (e.shiftKey) {
                // Shift+Tab
                if (document.activeElement === firstFocusable) {
                    e.preventDefault();
                    lastFocusable.focus();
                }
            } else {
                // Tab
                if (document.activeElement === lastFocusable) {
                    e.preventDefault();
                    firstFocusable.focus();
                }
            }
        }
    },

    handleBackdropClick(modalElement, e) {
        // Close modal if clicking on backdrop (not modal content)
        if (e.target === modalElement) {
            // Special handling for confirm modal
            if (modalElement.id === 'confirmModal' && typeof closeConfirmModal === 'function') {
                closeConfirmModal(false);
            } else {
                this.close(modalElement);
            }
        }
    },

    getFocusableElements(element) {
        const focusable = element.querySelectorAll(this.focusableSelectors);
        return Array.from(focusable).filter(el => {
            return !el.disabled && el.offsetParent !== null;
        });
    },

    disableBackground() {
        // Mark non-modal elements as inert
        const container = document.querySelector('.container');
        if (container) {
            // Blur any focused element within the container to prevent focus warnings
            if (document.activeElement && container.contains(document.activeElement)) {
                document.activeElement.blur();
            }

            // Use only inert (which handles both interaction and accessibility)
            // aria-hidden is redundant and causes warnings when elements have focus
            container.setAttribute('inert', '');
        }
    },

    enableBackground() {
        // Remove inert from background
        const container = document.querySelector('.container');
        if (container) {
            container.removeAttribute('inert');
        }
    }
};

// Animation Toggle Management
function initAnimationToggle() {
    const noAnimationToggle = document.getElementById('noAnimationToggle');
    const savedPreference = localStorage.getItem('noAnimations');

    // Apply saved preference
    if (savedPreference === 'true') {
        noAnimationToggle.checked = true;
        document.body.classList.add('no-animations');
    }
}

function toggleAnimations() {
    const noAnimationToggle = document.getElementById('noAnimationToggle');
    const isChecked = noAnimationToggle.checked;

    // Save preference
    localStorage.setItem('noAnimations', isChecked);

    // Apply or remove class
    if (isChecked) {
        document.body.classList.add('no-animations');
    } else {
        document.body.classList.remove('no-animations');

        // Force reflow to restart animations
        void document.body.offsetHeight;

        // Restart animations by temporarily removing and re-adding animated elements
        const animatedElements = document.querySelectorAll('.animated-bg, .logo-icon');
        animatedElements.forEach(el => {
            const parent = el.parentNode;
            const next = el.nextSibling;
            parent.removeChild(el);

            // Force reflow
            void parent.offsetHeight;

            // Re-insert element
            if (next) {
                parent.insertBefore(el, next);
            } else {
                parent.appendChild(el);
            }
        });
    }
}

// Switch Main Tabs
window.switchMainTab = function(tabName) {
    // Clear any existing system info refresh interval
    if (systemInfoRefreshInterval) {
        clearInterval(systemInfoRefreshInterval);
        systemInfoRefreshInterval = null;
    }

    // Hide all tab contents
    document.querySelectorAll('.main-tab-content').forEach(content => {
        content.classList.remove('active');
    });

    // Remove active class from all tab buttons
    document.querySelectorAll('.main-tab-button').forEach(button => {
        button.classList.remove('active');
    });

    // Show selected tab content
    const selectedTab = document.getElementById(`${tabName}-tab`);
    if (selectedTab) {
        selectedTab.classList.add('active');
    }

    // Add active class to clicked button
    const selectedButton = document.querySelector(`.main-tab-button[onclick="switchMainTab('${tabName}')"]`);
    if (selectedButton) {
        selectedButton.classList.add('active');
    }

    // Save active tab to localStorage
    localStorage.setItem('activeMainTab', tabName);

    // Load data for the selected tab
    if (tabName === 'system') {
        // Load immediately
        loadSystemInfo();
        // Set up auto-refresh every 15 seconds
        systemInfoRefreshInterval = setInterval(() => {
            loadSystemInfo();
        }, 15000);
    } else if (tabName === 'jobs') {
        loadJobs();
    } else if (tabName === 'files') {
        loadFiles(currentFolderPath || '');
    }
};

// Restore active tab on page load
window.restoreActiveTab = function() {
    const savedTab = localStorage.getItem('activeMainTab');
    if (savedTab && document.getElementById(`${savedTab}-tab`)) {
        switchMainTab(savedTab);
    }
};

// Toggle YouTube Options visibility
window.toggleYouTubeOptions = function() {
    const options = document.getElementById('youtubeOptions');
    const icon = document.getElementById('toggleYouTubeIcon');
    const text = document.getElementById('toggleYouTubeText');

    if (options.style.display === 'none') {
        options.style.display = 'block';
        icon.textContent = '▲';
        if (text) text.textContent = 'Hide';
    } else {
        options.style.display = 'none';
        icon.textContent = '▼';
        if (text) text.textContent = 'Show';
    }
};

// Toggle Transcription Parameters visibility
window.toggleTranscriptionParams = function() {
    const params = document.getElementById('transcriptionParams');
    const icon = document.getElementById('toggleParamsIcon');
    const text = document.getElementById('toggleParamsText');

    if (params.style.display === 'none') {
        params.style.display = 'block';
        icon.textContent = '▲';
        if (text) text.textContent = 'Hide';
    } else {
        params.style.display = 'none';
        icon.textContent = '▼';
        if (text) text.textContent = 'Show';
    }
};

// WebSocket connection with reconnection settings
const socket = io({
    reconnection: true,
    reconnectionDelay: 1000,
    reconnectionDelayMax: 5000,
    reconnectionAttempts: 5,
    transports: ['websocket', 'polling']  // Try websocket first, fallback to polling
});

// Global state
let jobs = [];
let files = [];
let currentTab = 'all';
// Removed currentSourceType - now always YouTube
let selectedFile = null;
let currentFilters = {
    bad_phrases: [],
    bad_patterns: []
};
let systemInfoRefreshInterval = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    // Initialize theme first
    initTheme();

    // Initialize animation toggle
    initAnimationToggle();

    // Restore active tab from localStorage
    restoreActiveTab();

    // Setup theme toggle buttons
    document.querySelectorAll('.theme-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            switchTheme(btn.dataset.theme);
        });
    });

    // Setup animation toggle checkbox
    const noAnimationToggle = document.getElementById('noAnimationToggle');
    if (noAnimationToggle) {
        noAnimationToggle.addEventListener('change', toggleAnimations);
    }

    // Listen for system theme changes when in auto mode
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
        const currentTheme = getCookie('theme');
        if (currentTheme === 'auto') {
            applyTheme('auto');
        }
    });

    // Setup inline checkbox styling (no class toggling needed, CSS handles it)
    const autoCleanupCheckbox = document.getElementById('auto_cleanup');
    if (autoCleanupCheckbox) {
        // Just log the change for debugging
        autoCleanupCheckbox.addEventListener('change', () => {
            console.log('Auto cleanup checkbox changed:', autoCleanupCheckbox.checked);
        });
    }

    loadConfig();
    loadJobs();

    // Restore last visited folder from localStorage
    const savedFolderPath = localStorage.getItem('currentFolderPath');
    loadFiles(savedFolderPath || '');

    checkCookieStatus();
    setupEventListeners();
    setupSocketListeners();

    // Start smart job polling
    startSmartJobPolling();

    // Cleanup interval on page unload
    window.addEventListener('beforeunload', () => {
        if (systemInfoRefreshInterval) {
            clearInterval(systemInfoRefreshInterval);
        }
    });
});

// Load configuration options
async function loadConfig() {
    try {
        const response = await fetch('/api/config');
        const config = await response.json();

        populateSelect('model', config.models);
        populateSelect('device', config.devices);
        populateSelect('language', config.languages);
        populateSelect('beam_size', config.beam_sizes);
        populateSelect('workers', config.workers);
        populateSelect('vad_filter', config.vad_options);
        populateSelect('compute_type', config.compute_types);
        populateSelect('temperature', config.temperatures);

        // Wait a tick to ensure DOM is updated
        await new Promise(resolve => setTimeout(resolve, 0));

        // Restore saved settings from localStorage
        restoreFormSettings();

        // Add change listeners to save settings
        setupSettingsSaver();

        // Setup VAD extended parameters toggle
        setupVADToggle();
    } catch (error) {
        console.error('Failed to load config:', error);
        showNotification('Failed to load configuration', 'error');
    }
}

// Setup VAD filter toggle to show/hide extended parameters
function setupVADToggle() {
    const vadFilter = document.getElementById('vad_filter');
    const vadExtended = document.getElementById('vad_extended_params');

    if (!vadFilter || !vadExtended) return;

    vadFilter.addEventListener('change', (e) => {
        const vadEnabled = e.target.value === 'true';
        vadExtended.style.display = vadEnabled ? 'block' : 'none';
    });

    // Trigger initial state
    const vadEnabled = vadFilter.value === 'true';
    vadExtended.style.display = vadEnabled ? 'block' : 'none';
}

// Restore form settings from localStorage
function restoreFormSettings() {
    const settings = {
        model: localStorage.getItem('transcription_model'),
        device: localStorage.getItem('transcription_device'),
        language: localStorage.getItem('transcription_language'),
        beam_size: localStorage.getItem('transcription_beam_size'),
        workers: localStorage.getItem('transcription_workers'),
        vad_filter: localStorage.getItem('transcription_vad_filter'),
        compute_type: localStorage.getItem('transcription_compute_type'),
        temperature: localStorage.getItem('transcription_temperature'),
        auto_cleanup: localStorage.getItem('transcription_auto_cleanup'),
        override_video: localStorage.getItem('transcription_override_video'),
        override_srt: localStorage.getItem('transcription_override_srt')
    };

    // Apply saved settings
    if (settings.model) document.getElementById('model').value = settings.model;
    if (settings.device) document.getElementById('device').value = settings.device;
    if (settings.language) document.getElementById('language').value = settings.language;
    if (settings.beam_size) document.getElementById('beam_size').value = settings.beam_size;
    if (settings.workers) document.getElementById('workers').value = settings.workers;
    if (settings.vad_filter) document.getElementById('vad_filter').value = settings.vad_filter;
    if (settings.compute_type) document.getElementById('compute_type').value = settings.compute_type;
    if (settings.temperature) document.getElementById('temperature').value = settings.temperature;

    // Restore checkbox states
    const autoCleanupCheckbox = document.getElementById('auto_cleanup');
    if (settings.auto_cleanup !== null) {
        autoCleanupCheckbox.checked = (settings.auto_cleanup === 'true');
    }

    const overrideVideoCheckbox = document.getElementById('override_video');
    if (overrideVideoCheckbox && settings.override_video !== null) {
        overrideVideoCheckbox.checked = (settings.override_video === 'true');
    }

    const overrideSrtCheckbox = document.getElementById('override_srt');
    if (overrideSrtCheckbox && settings.override_srt !== null) {
        overrideSrtCheckbox.checked = (settings.override_srt === 'true');
    }

    console.log('Settings restored:', settings);
}

// Setup listeners to save settings when changed
function setupSettingsSaver() {
    const settingFields = [
        'model', 'device', 'language', 'beam_size', 'workers',
        'vad_filter', 'compute_type', 'temperature'
    ];

    settingFields.forEach(fieldId => {
        const element = document.getElementById(fieldId);
        if (element) {
            element.addEventListener('change', () => {
                localStorage.setItem(`transcription_${fieldId}`, element.value);
            });
        }
    });

    // Save auto_cleanup checkbox
    const autoCleanup = document.getElementById('auto_cleanup');
    if (autoCleanup) {
        autoCleanup.addEventListener('change', () => {
            localStorage.setItem('transcription_auto_cleanup', autoCleanup.checked.toString());
            console.log('Auto cleanup saved:', autoCleanup.checked);
        });
    }

    // Save override_video checkbox
    const overrideVideo = document.getElementById('override_video');
    if (overrideVideo) {
        overrideVideo.addEventListener('change', () => {
            localStorage.setItem('transcription_override_video', overrideVideo.checked.toString());
            console.log('Override video saved:', overrideVideo.checked);
        });
    }

    // Save override_srt checkbox
    const overrideSrt = document.getElementById('override_srt');
    if (overrideSrt) {
        overrideSrt.addEventListener('change', () => {
            localStorage.setItem('transcription_override_srt', overrideSrt.checked.toString());
            console.log('Override SRT saved:', overrideSrt.checked);
        });
    }
}

// Populate select dropdown
function populateSelect(id, options) {
    const select = document.getElementById(id);
    select.innerHTML = '';

    options.forEach(opt => {
        const option = document.createElement('option');
        option.value = opt.value;
        option.textContent = opt.label;
        select.appendChild(option);
    });
}

// Setup event listeners
function setupEventListeners() {
    // Form submission
    document.getElementById('jobForm').addEventListener('submit', handleSubmit);

    // Source type tabs (if they exist)
    document.querySelectorAll('.source-tab-btn').forEach(btn => {
        btn.addEventListener('click', switchSourceTab);
    });

    // Video file upload (if it exists - legacy support)
    const videoFileInput = document.getElementById('video_file');
    if (videoFileInput) {
        videoFileInput.addEventListener('change', handleVideoFileSelect);
    }

    // Drag and drop (if it exists - legacy support)
    const dropZone = document.getElementById('fileDropZone');
    if (dropZone) {
        dropZone.addEventListener('dragover', handleDragOver);
        dropZone.addEventListener('dragleave', handleDragLeave);
        dropZone.addEventListener('drop', handleDrop);
    }

    // Cookie file input
    const cookieFileInput = document.getElementById('cookie_file');
    if (cookieFileInput) {
        cookieFileInput.addEventListener('change', handleFileSelect);
    }

    // File browser
    const refreshFilesBtn = document.getElementById('refreshFiles');
    if (refreshFilesBtn) refreshFilesBtn.addEventListener('click', loadFiles);

    const createFolderBtn = document.getElementById('createFolder');
    if (createFolderBtn) createFolderBtn.addEventListener('click', openCreateFolderModal);

    const fileSearchInput = document.getElementById('fileSearch');
    if (fileSearchInput) fileSearchInput.addEventListener('input', filterFiles);

    const fileTypeFilter = document.getElementById('fileTypeFilter');
    if (fileTypeFilter) fileTypeFilter.addEventListener('change', filterFiles);

    // Filter editor
    const openFilterBtn = document.getElementById('openFilterEditor');
    if (openFilterBtn) openFilterBtn.addEventListener('click', openFilterEditor);

    // Upload modal
    const openUploadBtn = document.getElementById('openUploadModal');
    if (openUploadBtn) openUploadBtn.addEventListener('click', openUploadModal);

    // Clear completed/failed jobs
    const clearJobsBtn = document.getElementById('clearCompletedJobs');
    if (clearJobsBtn) clearJobsBtn.addEventListener('click', clearCompletedFailedJobs);

    // Tabs
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.addEventListener('click', (e) => {
            currentTab = e.target.dataset.tab;
            document.querySelectorAll('.tab-button').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            renderJobs();
        });
    });

    // Modal close (if modal exists)
    const modalClose = document.querySelector('.modal-close');
    if (modalClose) {
        modalClose.addEventListener('click', closeModal);
    }

    window.addEventListener('click', (e) => {
        const modal = document.getElementById('jobModal');
        if (modal && e.target === modal) {
            closeModal();
        }
    });
}

// Update connection status indicator
function updateConnectionStatus(connected) {
    const statusEl = document.getElementById('connectionStatus');
    if (!statusEl) return;

    if (connected) {
        statusEl.className = 'connection-status connected';
        statusEl.title = 'Real-time updates active';
    } else {
        statusEl.className = 'connection-status disconnected';
        statusEl.title = 'Polling mode (updates every 2s)';
    }
}

// Setup Socket.IO listeners
function setupSocketListeners() {
    socket.on('connect', () => {
        console.log('✅ WebSocket connected to server, ID:', socket.id);
        updateConnectionStatus(true);
        // Refresh jobs when reconnected
        loadJobs();
    });

    socket.on('disconnect', (reason) => {
        console.log('⚠️  WebSocket disconnected from server. Reason:', reason);
        updateConnectionStatus(false);
        if (reason === 'io server disconnect') {
            // Server forcefully disconnected, reconnect manually
            socket.connect();
        }
    });

    socket.on('connect_error', (error) => {
        console.error('❌ WebSocket connection error:', error);
    });

    socket.on('error', (error) => {
        console.error('❌ WebSocket error:', error);
    });

    socket.on('job_created', (jobData) => {
        console.log('✨ New job created event received:', jobData.id);

        // Check if job already exists in local array
        const exists = jobs.find(j => j.id === jobData.id);
        if (exists) {
            console.log('   Job already in local array, skipping');
            return;
        }

        // Add new job to the beginning of the array
        console.log('   Adding new job to UI immediately');
        jobs.unshift(jobData);
        renderJobs();
    });

    socket.on('job_update', (data) => {
        console.log('🔄 Job update received:', {
            job_id: data.job_id,
            status: data.status,
            progress: data.progress,
            has_result: !!data.result,
            has_error: !!data.error
        });

        // Update job in local state
        const index = jobs.findIndex(j => j.id === data.job_id);
        if (index !== -1) {
            console.log(`   Updating job at index ${index}, old progress: ${jobs[index].progress}, new progress: ${data.progress}`);
            // Properly merge the update
            jobs[index] = {
                ...jobs[index],
                status: data.status,
                progress: data.progress,
                result: data.result || jobs[index].result,
                error: data.error || jobs[index].error
            };
        } else {
            console.warn('   Job not found in local jobs array!');

            // If this is a new job (status='queued'), fetch ONLY this job instead of reloading all
            if (data.status === 'queued') {
                console.log('   New job detected, fetching job details...');
                fetch(`/api/jobs/${data.job_id}`)
                    .then(res => res.json())
                    .then(jobData => {
                        console.log('   ✓ Fetched new job, adding to UI');
                        jobs.unshift(jobData);
                        renderJobs();
                    })
                    .catch(err => {
                        console.error('   Failed to fetch new job:', err);
                        // Fallback to full reload
                        loadJobs();
                    });
                return;
            } else {
                // For non-queued jobs, do a full reload
                console.log('   Job update for unknown job, reloading all jobs...');
                loadJobs();
                return;
            }
        }

        renderJobs();

        // Refresh files when job completes
        if (data.status === 'completed') {
            setTimeout(loadFiles, 2000);
        }
    });
}

// Switch source tab (YouTube vs Upload vs Existing)
function switchSourceTab(e) {
    const sourceType = e.currentTarget.dataset.source;
    currentSourceType = sourceType;

    // Update tab buttons
    document.querySelectorAll('.source-tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    e.currentTarget.classList.add('active');

    // Update content visibility
    document.querySelectorAll('.source-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(`${sourceType}-source`).classList.add('active');

    // Update form validation
    const urlInput = document.getElementById('url');
    const videoFileInput = document.getElementById('video_file');
    const existingFileSelect = document.getElementById('existing_file');

    if (sourceType === 'youtube') {
        urlInput.required = true;
        videoFileInput.required = false;
        if (existingFileSelect) existingFileSelect.required = false;
    } else if (sourceType === 'upload') {
        urlInput.required = false;
        videoFileInput.required = true;
        if (existingFileSelect) existingFileSelect.required = false;
    } else if (sourceType === 'existing') {
        urlInput.required = false;
        videoFileInput.required = false;
        if (existingFileSelect) existingFileSelect.required = true;
        // Load existing files if not already loaded
        loadExistingFilesForTranscription();
    }
}

// Load existing files for transcription dropdown
async function loadExistingFilesForTranscription() {
    const select = document.getElementById('existing_file');

    try {
        const response = await fetch('/api/files');
        const files = await response.json();

        // Filter only video/audio files without subtitles
        const videoExtensions = ['.mp4', '.mkv', '.avi', '.webm', '.mov', '.mp3', '.wav', '.m4a'];
        const availableFiles = files.filter(file =>
            videoExtensions.includes(file.type)
        );

        if (availableFiles.length === 0) {
            select.innerHTML = '<option value="">No files available</option>';
            return;
        }

        select.innerHTML = '<option value="">Select a file...</option>' +
            availableFiles.map(file => `
                <option value="${file.path}"
                    data-name="${file.name}"
                    data-size="${file.size}"
                    data-has-srt="${file.has_subtitles || false}">
                    ${file.name} ${file.has_subtitles ? '(has subtitles)' : ''}
                </option>
            `).join('');

        // Add change handler
        select.onchange = handleExistingFileSelect;
    } catch (error) {
        console.error('Failed to load existing files:', error);
        select.innerHTML = '<option value="">Error loading files</option>';
    }
}

// Handle existing file selection
function handleExistingFileSelect(e) {
    const select = e.target;
    const selectedOption = select.options[select.selectedIndex];
    const filePath = select.value;

    const infoDiv = document.getElementById('existingFileInfo');
    const fileNameDiv = document.getElementById('existingFileName');
    const fileDetailsDiv = document.getElementById('existingFileDetails');

    if (!filePath) {
        infoDiv.style.display = 'none';
        return;
    }

    const fileName = selectedOption.dataset.name;
    const fileSize = formatFileSize(parseInt(selectedOption.dataset.size));
    const hasSrt = selectedOption.dataset.hasSrt === 'true';

    fileNameDiv.textContent = fileName;
    fileDetailsDiv.innerHTML = `
        Size: ${fileSize}
        ${hasSrt ? '<span style="color: var(--success-start); margin-left: 10px;">✓ Has subtitles</span>' :
                    '<span style="color: var(--text-muted); margin-left: 10px;">⚠️ No subtitles</span>'}
    `;
    infoDiv.style.display = 'block';
}

// Preview existing file
window.playExistingFile = function() {
    const select = document.getElementById('existing_file');
    const filePath = select.value;

    if (filePath) {
        playVideo(filePath);
    }
};

// Handle video file selection
async function handleVideoFileSelect(e) {
    const file = e.target.files[0];
    if (!file) return;

    selectedFile = file;
    displaySelectedFile(file);

    // Detect audio tracks
    await detectAudioTracks(file);
}

// Display selected file info
function displaySelectedFile(file) {
    const dropZoneContent = document.querySelector('.drop-zone-content');
    const fileSelected = document.getElementById('fileSelected');
    const fileName = document.getElementById('selectedFileName');
    const fileSize = document.getElementById('selectedFileSize');

    dropZoneContent.style.display = 'none';
    fileSelected.style.display = 'flex';
    fileName.textContent = file.name;
    fileSize.textContent = formatFileSize(file.size);
}

// Clear file selection
window.clearFileSelection = function() {
    const videoFileInput = document.getElementById('video_file');
    videoFileInput.value = '';
    selectedFile = null;

    const dropZoneContent = document.querySelector('.drop-zone-content');
    const fileSelected = document.getElementById('fileSelected');
    const audioTrackGroup = document.getElementById('audioTrackGroup');

    dropZoneContent.style.display = 'flex';
    fileSelected.style.display = 'none';
    audioTrackGroup.style.display = 'none';
}

// Detect audio tracks in uploaded file
async function detectAudioTracks(file) {
    const audioTrackGroup = document.getElementById('audioTrackGroup');
    const audioTrackSelect = document.getElementById('audio_track');

    try {
        // Show loading state
        audioTrackGroup.style.display = 'block';
        audioTrackSelect.innerHTML = '<option value="">Detecting audio tracks...</option>';

        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch('/api/detect-audio-tracks', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.tracks && data.tracks.length > 0) {
            // Populate audio track dropdown
            audioTrackSelect.innerHTML = '';
            data.tracks.forEach((track, index) => {
                const option = document.createElement('option');
                option.value = track.index;

                let label = `Track ${track.index + 1}`;
                if (track.language) {
                    label += ` (${track.language})`;
                }
                if (track.title) {
                    label += ` - ${track.title}`;
                }
                label += ` | ${track.codec_name}, ${track.channels}ch`;

                option.textContent = label;
                audioTrackSelect.appendChild(option);
            });

            if (data.tracks.length === 1) {
                audioTrackGroup.style.display = 'none'; // Hide if only one track
            }
        } else {
            audioTrackSelect.innerHTML = '<option value="0">Default audio track</option>';
        }
    } catch (error) {
        console.error('Failed to detect audio tracks:', error);
        audioTrackSelect.innerHTML = '<option value="0">Default audio track</option>';
    }
}

// Drag and drop handlers
function handleDragOver(e) {
    e.preventDefault();
    e.stopPropagation();
    e.currentTarget.classList.add('drag-over');
}

function handleDragLeave(e) {
    e.preventDefault();
    e.stopPropagation();
    e.currentTarget.classList.remove('drag-over');
}

function handleDrop(e) {
    e.preventDefault();
    e.stopPropagation();
    e.currentTarget.classList.remove('drag-over');

    const files = e.dataTransfer.files;
    if (files.length > 0) {
        const videoFileInput = document.getElementById('video_file');
        videoFileInput.files = files;

        // Trigger change event
        const event = new Event('change', { bubbles: true });
        videoFileInput.dispatchEvent(event);
    }
}

// Handle form submission
async function handleSubmit(e) {
    e.preventDefault();

    const formData = new FormData(e.target);

    // Always use YouTube source type (simplified interface)
    formData.append('source_type', 'youtube');

    // Validate YouTube URL
    const url = formData.get('url');
    if (!url || url.trim() === '') {
        showNotification('Please enter a YouTube URL', 'error');
        return;
    }

    // Show loading state
    const submitBtn = e.target.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    submitBtn.innerHTML = '<span>⏳ Submitting...</span>';
    submitBtn.disabled = true;

    try {
        const response = await fetch('/api/submit', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (response.ok) {
            showNotification('Job submitted successfully!', 'success');
            e.target.reset();
            document.getElementById('fileName').textContent = 'Upload cookies.txt';

            // Refresh cookie status if a cookie was uploaded
            checkCookieStatus();

            // Optimistically add the new job to the UI immediately
            const newJob = {
                id: data.job_id,
                url: formData.get('url'),
                status: 'queued',
                progress: 0,
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString(),
                parameters: JSON.stringify({
                    model: formData.get('model'),
                    device: formData.get('device'),
                    language: formData.get('language'),
                    video_title: 'Loading...'
                }),
                job_type: 'download',
                result: null,
                error: null
            };

            // Add to jobs array and render immediately
            console.log('✨ Adding new job to UI immediately:', data.job_id);
            jobs.unshift(newJob);
            renderJobs();

            // Switch to Jobs tab to show the new job
            switchMainTab('jobs');

            // Also fetch from server to get complete data (including video title)
            console.log('⏱️ Scheduling full job refresh in 500ms...');
            setTimeout(() => {
                console.log('🔄 Fetching complete job data from server...');
                loadJobs();
            }, 500);
        } else {
            showNotification(data.error || 'Failed to submit job', 'error');
        }
    } catch (error) {
        console.error('Submit error:', error);
        showNotification('Failed to submit job', 'error');
    } finally {
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
    }
}

// Handle existing file and audio stream detection
async function handleExistingFileStreams(formEvent, formData, filePath) {
    const submitBtn = formEvent.target.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    submitBtn.innerHTML = '<span>⏳ Detecting audio streams...</span>';
    submitBtn.disabled = true;

    try {
        showNotification('Analyzing audio streams...', 'success');

        const detectResponse = await fetch('/api/detect-audio-streams-existing', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ file_path: filePath })
        });

        if (!detectResponse.ok) {
            const error = await detectResponse.json();
            showNotification(error.error || 'Failed to detect audio streams', 'error');
            return;
        }

        const detectData = await detectResponse.json();

        // Show audio stream selection modal
        showAudioStreamSelectionModalForExisting(detectData.tracks, filePath, formData);

    } catch (error) {
        console.error('Stream detection error:', error);
        showNotification('Failed to detect audio streams', 'error');
    } finally {
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
    }
}

// Show modal for audio stream selection (existing file)
function showAudioStreamSelectionModalForExisting(tracks, filePath, originalFormData) {
    // Create modal HTML
    const modalHTML = `
        <div id="audioStreamModal" class="modal show">
            <div class="modal-content" style="max-width: 700px;">
                <span class="modal-close" onclick="closeAudioStreamModal()">&times;</span>
                <h2>🎧 Select Audio Stream</h2>
                <p class="modal-subtitle">Found ${tracks.length} audio stream(s) in this file</p>

                <div style="margin: 20px 0;">
                    ${tracks.map((track, index) => {
                        const language = track.language !== 'und' ? track.language.toUpperCase() : 'Unknown';
                        const title = track.title || `Audio Track ${index + 1}`;
                        const channels = track.channels === 1 ? 'Mono' : track.channels === 2 ? 'Stereo' : `${track.channels}ch`;

                        return `
                            <label class="audio-stream-option" style="display: block; padding: 15px; margin-bottom: 10px; background: rgba(255,255,255,0.05); border: 2px solid var(--border-color); border-radius: 12px; cursor: pointer; transition: all 0.3s;">
                                <input type="radio" name="audio_stream" value="${track.index}" ${index === 0 ? 'checked' : ''} style="margin-right: 10px;">
                                <strong style="font-size: 1.1rem;">${title}</strong>
                                <div style="margin-top: 5px; color: var(--text-secondary); font-size: 0.9rem;">
                                    Stream ${track.index} • ${language} • ${channels} • ${track.codec} • ${(track.sample_rate / 1000).toFixed(1)} kHz
                                </div>
                            </label>
                        `;
                    }).join('')}
                </div>

                <div style="text-align: right; margin-top: 20px;">
                    <button onclick="closeAudioStreamModal()" class="btn btn-secondary">Cancel</button>
                    <button onclick="submitWithSelectedStreamExisting('${filePath}')" class="btn btn-primary">Start Transcription</button>
                </div>
            </div>
        </div>
    `;

    // Add modal to page
    const existingModal = document.getElementById('audioStreamModal');
    if (existingModal) {
        existingModal.remove();
    }

    document.body.insertAdjacentHTML('beforeend', modalHTML);

    // Store original form data for later
    window.pendingTranscriptionFormData = originalFormData;

    // Add hover effect to options
    document.querySelectorAll('.audio-stream-option').forEach(option => {
        option.addEventListener('mouseenter', function() {
            this.style.background = 'rgba(102, 126, 234, 0.1)';
            this.style.borderColor = 'var(--primary-start)';
        });
        option.addEventListener('mouseleave', function() {
            const radio = this.querySelector('input[type="radio"]');
            if (!radio.checked) {
                this.style.background = 'rgba(255,255,255,0.05)';
                this.style.borderColor = 'var(--border-color)';
            }
        });
        option.addEventListener('click', function() {
            document.querySelectorAll('.audio-stream-option').forEach(opt => {
                opt.style.background = 'rgba(255,255,255,0.05)';
                opt.style.borderColor = 'var(--border-color)';
            });
            this.style.background = 'rgba(102, 126, 234, 0.1)';
            this.style.borderColor = 'var(--primary-start)';
            this.querySelector('input[type="radio"]').checked = true;
        });
    });
}

async function submitWithSelectedStreamExisting(filePath) {
    const selectedStream = document.querySelector('input[name="audio_stream"]:checked');
    if (!selectedStream) {
        showNotification('Please select an audio stream', 'error');
        return;
    }

    const streamIndex = selectedStream.value;
    const formData = window.pendingTranscriptionFormData;

    // Add selected audio stream
    formData.set('audio_track', streamIndex);
    formData.set('existing_file_path', filePath);

    // Close modal
    closeAudioStreamModal();

    // Show loading
    showNotification('Starting transcription...', 'success');

    try {
        const response = await fetch('/api/submit', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (response.ok) {
            showNotification('Transcription job started!', 'success');

            // Reset form
            const form = document.getElementById('jobForm');
            form.reset();
            document.getElementById('fileName').textContent = 'Upload cookies.txt';
            document.getElementById('existingFileInfo').style.display = 'none';

            // Refresh cookie status and jobs
            checkCookieStatus();
            loadJobs();
        } else {
            showNotification(data.error || 'Failed to start transcription', 'error');
        }
    } catch (error) {
        console.error('Submit error:', error);
        showNotification('Failed to start transcription', 'error');
    }
}

// Handle file upload and audio stream detection
async function handleUploadAndDetectStreams(formEvent, formData) {
    const submitBtn = formEvent.target.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    submitBtn.innerHTML = '<span>⏳ Uploading file...</span>';
    submitBtn.disabled = true;

    try {
        // Step 1: Upload file to temporary location
        const videoFile = formData.get('video_file');
        const uploadFormData = new FormData();
        uploadFormData.append('file', videoFile);

        showNotification('Uploading file...', 'success');

        const uploadResponse = await fetch('/api/upload-temp', {
            method: 'POST',
            body: uploadFormData
        });

        if (!uploadResponse.ok) {
            const error = await uploadResponse.json();
            showNotification(error.error || 'Failed to upload file', 'error');
            return;
        }

        const uploadData = await uploadResponse.json();
        const tempFilePath = uploadData.temp_path;

        // Step 2: Detect audio streams
        submitBtn.innerHTML = '<span>⏳ Detecting audio streams...</span>';
        showNotification('Analyzing audio streams...', 'success');

        const detectResponse = await fetch('/api/detect-audio-streams', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ temp_path: tempFilePath })
        });

        if (!detectResponse.ok) {
            const error = await detectResponse.json();
            showNotification(error.error || 'Failed to detect audio streams', 'error');
            return;
        }

        const detectData = await detectResponse.json();

        // Step 3: Show audio stream selection modal
        showAudioStreamSelectionModal(detectData.tracks, tempFilePath, formData);

    } catch (error) {
        console.error('Upload and detect error:', error);
        showNotification('Failed to process file', 'error');
    } finally {
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
    }
}

// Show modal for audio stream selection
function showAudioStreamSelectionModal(tracks, tempFilePath, originalFormData) {
    // Create modal HTML
    const modalHTML = `
        <div id="audioStreamModal" class="modal show">
            <div class="modal-content" style="max-width: 700px;">
                <span class="modal-close" onclick="closeAudioStreamModal()">&times;</span>
                <h2>🎧 Select Audio Stream</h2>
                <p class="modal-subtitle">Found ${tracks.length} audio stream(s) in this file</p>

                <div style="margin: 20px 0;">
                    ${tracks.map((track, index) => {
                        const language = track.language !== 'und' ? track.language.toUpperCase() : 'Unknown';
                        const title = track.title || `Audio Track ${index + 1}`;
                        const channels = track.channels === 1 ? 'Mono' : track.channels === 2 ? 'Stereo' : `${track.channels}ch`;

                        return `
                            <label class="audio-stream-option" style="display: block; padding: 15px; margin-bottom: 10px; background: rgba(255,255,255,0.05); border: 2px solid var(--border-color); border-radius: 12px; cursor: pointer; transition: all 0.3s;">
                                <input type="radio" name="audio_stream" value="${track.index}" ${index === 0 ? 'checked' : ''} style="margin-right: 10px;">
                                <strong style="font-size: 1.1rem;">${title}</strong>
                                <div style="margin-top: 5px; color: var(--text-secondary); font-size: 0.9rem;">
                                    Stream ${track.index} • ${language} • ${channels} • ${track.codec} • ${(track.sample_rate / 1000).toFixed(1)} kHz
                                </div>
                            </label>
                        `;
                    }).join('')}
                </div>

                <div style="text-align: right; margin-top: 20px;">
                    <button onclick="closeAudioStreamModal()" class="btn btn-secondary">Cancel</button>
                    <button onclick="submitWithSelectedStream('${tempFilePath}')" class="btn btn-primary">Start Transcription</button>
                </div>
            </div>
        </div>
    `;

    // Add modal to page
    const existingModal = document.getElementById('audioStreamModal');
    if (existingModal) {
        existingModal.remove();
    }

    document.body.insertAdjacentHTML('beforeend', modalHTML);

    // Store original form data for later
    window.pendingTranscriptionFormData = originalFormData;

    // Add hover effect to options
    document.querySelectorAll('.audio-stream-option').forEach(option => {
        option.addEventListener('mouseenter', function() {
            this.style.background = 'rgba(102, 126, 234, 0.1)';
            this.style.borderColor = 'var(--primary-start)';
        });
        option.addEventListener('mouseleave', function() {
            const radio = this.querySelector('input[type="radio"]');
            if (!radio.checked) {
                this.style.background = 'rgba(255,255,255,0.05)';
                this.style.borderColor = 'var(--border-color)';
            }
        });
        option.addEventListener('click', function() {
            document.querySelectorAll('.audio-stream-option').forEach(opt => {
                opt.style.background = 'rgba(255,255,255,0.05)';
                opt.style.borderColor = 'var(--border-color)';
            });
            this.style.background = 'rgba(102, 126, 234, 0.1)';
            this.style.borderColor = 'var(--primary-start)';
            this.querySelector('input[type="radio"]').checked = true;
        });
    });
}

function closeAudioStreamModal() {
    const modal = document.getElementById('audioStreamModal');
    if (modal) {
        modal.remove();
    }
    window.pendingTranscriptionFormData = null;
}

async function submitWithSelectedStream(tempFilePath) {
    const selectedStream = document.querySelector('input[name="audio_stream"]:checked');
    if (!selectedStream) {
        showNotification('Please select an audio stream', 'error');
        return;
    }

    const streamIndex = selectedStream.value;
    const formData = window.pendingTranscriptionFormData;

    // Add selected audio stream and temp file path to form data
    formData.set('audio_track', streamIndex);
    formData.set('temp_file_path', tempFilePath);

    // Close modal
    closeAudioStreamModal();

    // Show loading
    showNotification('Starting transcription...', 'success');

    try {
        const response = await fetch('/api/submit', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (response.ok) {
            showNotification('Transcription job started!', 'success');

            // Reset form
            const form = document.getElementById('jobForm');
            form.reset();
            document.getElementById('fileName').textContent = 'Upload cookies.txt';
            clearFileSelection();

            // Refresh cookie status and jobs
            checkCookieStatus();
            loadJobs();
        } else {
            showNotification(data.error || 'Failed to start transcription', 'error');
        }
    } catch (error) {
        console.error('Submit error:', error);
        showNotification('Failed to start transcription', 'error');
    }
}

// Check cookie file status
async function checkCookieStatus() {
    try {
        const response = await fetch('/api/cookie-status');
        const data = await response.json();

        const statusDiv = document.getElementById('cookieStatus');
        const statusInfo = statusDiv.querySelector('.cookie-info');

        if (data.exists) {
            statusDiv.className = 'cookie-status has-cookie';
            statusInfo.innerHTML = `✅ Cookie file active: <strong>${data.filename}</strong> (${data.size})`;
        } else {
            statusDiv.className = 'cookie-status no-cookie';
            statusInfo.innerHTML = '⚠️ No cookie file found - upload one for age-restricted videos';
        }
    } catch (error) {
        console.error('Failed to check cookie status:', error);
    }
}

// Handle file input change
function handleFileSelect(e) {
    const file = e.target.files[0];
    const fileName = document.getElementById('fileName');

    if (file) {
        fileName.textContent = file.name;
    } else {
        fileName.textContent = 'Upload cookies.txt';
    }
}

// Load jobs from server
async function loadJobs() {
    try {
        const response = await fetch('/api/jobs');
        jobs = await response.json();
        console.log('Loaded jobs:', jobs.length, 'jobs');
        console.log('Jobs array:', jobs);
        renderJobs();
    } catch (error) {
        console.error('Failed to load jobs:', error);
    }
}

// Smart job polling - adjusts frequency based on active jobs
let pollingInterval = null;
let currentPollingRate = 10000; // Start with 10 seconds

function startSmartJobPolling() {
    // Clear any existing interval
    if (pollingInterval) {
        clearInterval(pollingInterval);
    }

    // Function to determine polling rate
    const updatePollingRate = () => {
        const activeJobs = jobs.filter(j => ['queued', 'running'].includes(j.status));

        // Fast polling (2 seconds) when there are active jobs
        // Slow polling (30 seconds) when all jobs are complete
        const newRate = activeJobs.length > 0 ? 2000 : 30000;

        if (newRate !== currentPollingRate) {
            currentPollingRate = newRate;
            console.log(`📊 Polling rate adjusted to ${currentPollingRate / 1000}s (${activeJobs.length} active jobs)`);

            // Restart interval with new rate
            clearInterval(pollingInterval);
            pollingInterval = setInterval(pollAndUpdate, currentPollingRate);
        }
    };

    // Polling function
    const pollAndUpdate = async () => {
        try {
            const activeJobsCount = jobs.filter(j => ['queued', 'running'].includes(j.status)).length;
            if (activeJobsCount > 0) {
                console.log(`🔄 Polling jobs... (${activeJobsCount} active)`);
            }
            await loadJobs();
            updatePollingRate();
        } catch (error) {
            console.error('❌ Error in polling:', error);
        }
    };

    // Start polling immediately, then continue at intervals
    pollAndUpdate();

    console.log('✅ Smart job polling started at 2s intervals');
}

// Render jobs list
function renderJobs() {
    console.log('renderJobs called');
    console.log('Total jobs:', jobs.length);

    // Separate active and completed jobs
    const activeJobs = jobs.filter(j => ['queued', 'running'].includes(j.status));
    const completedJobs = jobs.filter(j => !['queued', 'running'].includes(j.status));

    console.log('Active jobs:', activeJobs.length);
    console.log('Completed jobs:', completedJobs.length);

    // Render active jobs
    const activeContainer = document.getElementById('activeJobs');
    console.log('activeContainer:', activeContainer);
    if (activeJobs.length === 0) {
        activeContainer.innerHTML = '<p class="no-data">No active jobs</p>';
    } else {
        activeContainer.innerHTML = activeJobs.map(renderJobItem).join('');
    }

    // Filter completed jobs by tab
    let filteredJobs = completedJobs;
    console.log('currentTab:', currentTab);
    if (currentTab === 'completed') {
        filteredJobs = completedJobs.filter(j => j.status === 'completed');
    } else if (currentTab === 'failed') {
        // Include both failed and cancelled jobs in the 'failed' tab
        filteredJobs = completedJobs.filter(j => j.status === 'failed' || j.status === 'cancelled');
    }

    console.log('Filtered jobs for display:', filteredJobs.length);

    // Render job history
    const historyContainer = document.getElementById('jobHistory');
    console.log('historyContainer:', historyContainer);
    if (filteredJobs.length === 0) {
        historyContainer.innerHTML = '<p class="no-data">No jobs found</p>';
    } else {
        historyContainer.innerHTML = filteredJobs.map(renderJobItem).join('');
    }
    console.log('renderJobs complete');
}

// Render single job item
function renderJobItem(job) {
    let params = {};
    try {
        params = job.parameters ? JSON.parse(job.parameters) : {};
    } catch (e) {
        console.warn('Failed to parse job parameters for job', job.id, ':', e);
        params = {}; // Use empty object if parsing fails
    }
    const progress = job.progress || 0;

    // Extract video title from parameters or URL
    let videoTitle = params.video_title;
    if (!videoTitle || videoTitle === 'Unknown Video') {
        // Try to extract filename from URL
        if (job.url) {
            const urlMatch = job.url.match(/[^\\/]+\.(mp4|mkv|avi|webm|mov)/i);
            if (urlMatch) {
                videoTitle = urlMatch[0];
                // Remove YouTube ID pattern [xxx] from filename
                videoTitle = videoTitle.replace(/\s*\[[a-zA-Z0-9_-]{11}\]\.(mp4|mkv|avi|webm|mov)/i, '.$1');
            } else {
                // Just get the last part of the URL
                videoTitle = job.url.split(/[\\/]/).pop().substring(0, 60);
            }
        }
    }
    if (!videoTitle) {
        videoTitle = 'Unknown Video';
    }

    // Extract last log message from result field
    let lastMessage = '';
    if (job.result && job.result.trim()) {
        const lines = job.result.trim().split('\n').filter(line => line.trim());
        if (lines.length > 0) {
            lastMessage = lines[lines.length - 1].substring(0, 150); // Last line, max 150 chars
        }
    }

    // Determine job type badge
    const jobType = job.job_type || 'transcribe';
    let jobTypeBadge = '';
    if (jobType === 'download') {
        jobTypeBadge = '<span class="job-type-badge badge-download" title="Download job">📥 Download</span>';
    } else if (jobType === 'transcribe') {
        jobTypeBadge = '<span class="job-type-badge badge-transcribe" title="Transcription job">🎙️ Transcribe</span>';
    }

    return `
        <div class="job-item" onclick="showJobDetails('${job.id}')">
            <div class="job-header">
                <div class="job-title">
                    ${escapeHtml(videoTitle)}
                    ${jobTypeBadge}
                </div>
                <span class="job-status status-${job.status}">${job.status}</span>
            </div>
            <div class="job-url-small">${truncateUrl(job.url, 60)}</div>
            ${['queued', 'running'].includes(job.status) ? `
                <div class="job-progress">
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${progress}%"></div>
                    </div>
                    <small>${progress}%</small>
                </div>
            ` : ''}
            ${lastMessage ? `
                <div class="job-last-message">
                    <span class="message-icon">📝</span>
                    <span class="message-text">${escapeHtml(lastMessage)}</span>
                </div>
            ` : ''}
            <div class="job-meta">
                <span class="meta-tag">📊 ${params.model || 'N/A'}</span>
                <span class="meta-tag">💻 ${params.device || 'N/A'}</span>
                ${params.workers > 1 ? `<span class="meta-tag">👥 ${params.workers}</span>` : ''}
                <span class="meta-tag">🕐 ${formatDate(job.created_at)}</span>
            </div>
            ${job.error ? `
                <div style="margin-top: 10px; color: var(--error-color); font-size: 0.875rem;">
                    ❌ ${job.error.substring(0, 100)}${job.error.length > 100 ? '...' : ''}
                </div>
            ` : ''}
        </div>
    `;
}

// Helper function to escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Show job details modal
async function showJobDetails(jobId) {
    try {
        const response = await fetch(`/api/jobs/${jobId}`);
        const job = await response.json();

        let params = {};
        try {
            params = job.parameters ? JSON.parse(job.parameters) : {};
        } catch (e) {
            console.warn('Failed to parse job parameters:', e);
            params = { error: 'Invalid parameters data' };
        }

        const detailsHTML = `
            <div>
                <p><strong>Job ID:</strong> ${job.id}</p>
                <p><strong>URL:</strong> ${job.url}</p>
                <p><strong>Status:</strong> <span class="job-status status-${job.status}">${job.status}</span></p>
                <p><strong>Progress:</strong> ${job.progress || 0}%</p>
                <p><strong>Created:</strong> ${formatDate(job.created_at)}</p>
                <p><strong>Updated:</strong> ${formatDate(job.updated_at)}</p>

                <h3 style="margin-top: 20px;">Parameters</h3>
                <pre style="background: var(--bg-color); padding: 15px; border-radius: 6px; overflow-x: auto;">${JSON.stringify(params, null, 2)}</pre>

                ${job.result ? `
                    <h3 style="margin-top: 20px;">Output</h3>
                    <pre style="background: var(--bg-color); padding: 15px; border-radius: 6px; max-height: 300px; overflow-y: auto;">${job.result}</pre>
                ` : ''}

                ${job.error ? `
                    <h3 style="margin-top: 20px;">Error</h3>
                    <pre class="error-output">${job.error}</pre>
                ` : ''}

                <h3 style="margin-top: 20px;">Job Logs</h3>
                <div style="margin-bottom: 15px; display: flex; gap: 10px;">
                    <button onclick="loadJobLogs('${job.id}')" class="btn btn-secondary" id="loadLogsBtn_${job.id}">
                        📋 Load Logs
                    </button>
                    <button onclick="copyJobLogsToClipboard('${job.id}')" class="btn btn-secondary" id="copyLogsBtn_${job.id}" style="display: none;">
                        📋 Copy Log to Clipboard
                    </button>
                </div>
                <div id="jobLogs_${job.id}" style="display: none;">
                    <pre style="background: var(--bg-color); padding: 15px; border-radius: 6px; max-height: 400px; overflow-y: auto; font-size: 0.85rem; line-height: 1.4;" id="jobLogsContent_${job.id}">Loading...</pre>
                </div>

                <div style="margin-top: 30px; display: flex; gap: 10px; justify-content: flex-end;">
                    ${['queued', 'running'].includes(job.status) ? `
                        <button onclick="cancelJob('${job.id}')" class="btn" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
                            ⏹️ Stop Job
                        </button>
                    ` : ''}
                    ${job.job_type === 'download' && job.status === 'completed' ? `
                        <button onclick="createTranscriptionFromDownload('${job.id}')" class="btn btn-primary">
                            🎙️ Create Transcription Jobs
                        </button>
                    ` : ''}
                    ${['completed', 'failed', 'cancelled'].includes(job.status) ? `
                        <button onclick="restartJob('${job.id}')" class="btn btn-primary">
                            🔄 Restart Job
                        </button>
                    ` : ''}
                    <button onclick="deleteJob('${job.id}')" class="btn" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
                        🗑️ Delete Job
                    </button>
                    <button onclick="closeModal()" class="btn btn-secondary">Close</button>
                </div>
            </div>
        `;

        document.getElementById('jobDetails').innerHTML = detailsHTML;
        document.getElementById('jobModal').classList.add('show');
    } catch (error) {
        console.error('Failed to load job details:', error);
        showNotification('Failed to load job details', 'error');
    }
}

// Load job logs from server
async function loadJobLogs(jobId) {
    const logsDiv = document.getElementById(`jobLogs_${jobId}`);
    const logsContent = document.getElementById(`jobLogsContent_${jobId}`);
    const loadBtn = document.getElementById(`loadLogsBtn_${jobId}`);
    const copyBtn = document.getElementById(`copyLogsBtn_${jobId}`);

    try {
        // Show loading state
        logsDiv.style.display = 'block';
        logsContent.textContent = 'Loading logs...';
        loadBtn.disabled = true;
        loadBtn.textContent = '⏳ Loading...';

        const response = await fetch(`/api/jobs/${jobId}/logs`);

        if (!response.ok) {
            const error = await response.json();
            logsContent.textContent = `Error: ${error.message || 'Failed to load logs'}`;
            loadBtn.textContent = '📋 Retry';
            loadBtn.disabled = false;
            return;
        }

        const data = await response.json();
        logsContent.textContent = data.logs || 'No logs available';

        // Update button to allow hiding logs
        loadBtn.textContent = '🔼 Hide Logs';
        loadBtn.onclick = () => hideJobLogs(jobId);
        loadBtn.disabled = false;

        // Show copy button
        if (copyBtn) {
            copyBtn.style.display = 'inline-block';
        }

    } catch (error) {
        console.error('Failed to load job logs:', error);
        logsContent.textContent = `Error: ${error.message}`;
        loadBtn.textContent = '📋 Retry';
        loadBtn.disabled = false;
    }
}

// Hide job logs
function hideJobLogs(jobId) {
    const logsDiv = document.getElementById(`jobLogs_${jobId}`);
    const loadBtn = document.getElementById(`loadLogsBtn_${jobId}`);
    const copyBtn = document.getElementById(`copyLogsBtn_${jobId}`);

    logsDiv.style.display = 'none';
    loadBtn.textContent = '📋 Load Logs';
    loadBtn.onclick = () => loadJobLogs(jobId);

    // Hide copy button
    if (copyBtn) {
        copyBtn.style.display = 'none';
    }
}

// Copy job logs to clipboard
async function copyJobLogsToClipboard(jobId) {
    const logsContent = document.getElementById(`jobLogsContent_${jobId}`);
    const copyBtn = document.getElementById(`copyLogsBtn_${jobId}`);

    if (!logsContent) {
        showNotification('No logs to copy', 'error');
        return;
    }

    try {
        const logText = logsContent.textContent;

        // Use the Clipboard API
        await navigator.clipboard.writeText(logText);

        // Visual feedback
        const originalText = copyBtn.textContent;
        copyBtn.textContent = '✅ Copied!';
        copyBtn.disabled = true;

        setTimeout(() => {
            copyBtn.textContent = originalText;
            copyBtn.disabled = false;
        }, 2000);

        showNotification('Logs copied to clipboard', 'success');
    } catch (error) {
        console.error('Failed to copy logs:', error);
        showNotification('Failed to copy logs to clipboard', 'error');
    }
}

// Create transcription jobs from completed download job
async function createTranscriptionFromDownload(jobId) {
    try {
        const response = await fetch(`/api/jobs/${jobId}/create-transcription`, {
            method: 'POST'
        });
        const data = await response.json();

        if (response.ok) {
            const count = data.job_ids ? data.job_ids.length : 0;
            if (count > 0) {
                showNotification(`✅ Created ${count} transcription job${count > 1 ? 's' : ''}`, 'success');
                await loadJobs(); // Refresh job list
                closeModal();
            } else {
                showNotification('⚠️ No video files found to transcribe', 'warning');
            }
        } else {
            showNotification(`❌ ${data.error || 'Failed to create transcription jobs'}`, 'error');
        }
    } catch (error) {
        console.error('Error creating transcription jobs:', error);
        showNotification('❌ Failed to create transcription jobs', 'error');
    }
}

// Close modal
function closeModal() {
    const modal = document.getElementById('jobModal');
    ModalManager.close(modal);
}

// Load files from server
// Current folder path for file browser navigation
let currentFolderPath = '';

async function loadFiles(folderPath = '') {
    try {
        const url = folderPath ? `/api/files?path=${encodeURIComponent(folderPath)}` : '/api/files';
        const response = await fetch(url);
        const data = await response.json();

        currentFolderPath = data.current_path || '';

        // Save current folder path to localStorage
        if (currentFolderPath) {
            localStorage.setItem('currentFolderPath', currentFolderPath);
        } else {
            localStorage.removeItem('currentFolderPath');
        }

        files = data.items || [];
        renderFiles();
    } catch (error) {
        console.error('Failed to load files:', error);
    }
}

// Filter files
function filterFiles() {
    renderFiles();
}

// Render files list
function renderFiles() {
    const searchTerm = document.getElementById('fileSearch').value.toLowerCase();
    const typeFilter = document.getElementById('fileTypeFilter').value;

    let filteredFiles = files;

    // Apply search filter
    if (searchTerm) {
        filteredFiles = filteredFiles.filter(f =>
            f.name.toLowerCase().includes(searchTerm) ||
            f.path.toLowerCase().includes(searchTerm)
        );
    }

    // Apply type filter (don't filter folders)
    if (typeFilter !== 'all') {
        filteredFiles = filteredFiles.filter(f => f.type === 'folder' || f.type === typeFilter);
    }

    // Filter out subtitle files that belong to existing videos
    // Extract all video base names (without extension)
    const videoExtensions = ['.mp4', '.mkv', '.avi', '.webm', '.mov'];
    const videoBaseNames = new Set();

    filteredFiles.forEach(f => {
        if (f.type && videoExtensions.includes(f.type)) {
            // Get base name without extension
            const baseName = f.name.replace(/\.[^/.]+$/, '');
            videoBaseNames.add(baseName.toLowerCase());
        }
    });

    // Filter out subtitle files that match video base names
    filteredFiles = filteredFiles.filter(f => {
        const subtitleExtensions = ['.srt', '.vtt', '.ass'];
        if (f.type && subtitleExtensions.includes(f.type)) {
            // Check if this subtitle belongs to a video
            // Remove language suffix (e.g., .rus, .sr, .en, .srp) and extension
            let baseName = f.name.replace(/\.[^/.]+$/, ''); // Remove .srt
            baseName = baseName.replace(/\.[a-z]{2,3}$/i, ''); // Remove 2 or 3-letter language code

            // If a video with this base name exists, hide the subtitle
            if (videoBaseNames.has(baseName.toLowerCase())) {
                return false; // Filter out this subtitle
            }
        }
        return true; // Keep everything else
    });

    const container = document.getElementById('fileBrowser');

    // Build breadcrumb navigation
    let breadcrumb = '';
    if (currentFolderPath) {
        const parts = currentFolderPath.split('/');
        let accumulated = '';
        breadcrumb = `<div class="folder-breadcrumb">
            <button onclick="loadFiles('')" class="breadcrumb-btn">🏠 Root</button>`;
        for (let i = 0; i < parts.length; i++) {
            accumulated += (i > 0 ? '/' : '') + parts[i];
            breadcrumb += ` / <button onclick="loadFiles('${accumulated.replace(/'/g, "\\'")}')" class="breadcrumb-btn">${parts[i]}</button>`;
        }
        breadcrumb += `</div>`;
    } else {
        breadcrumb = `<div class="folder-breadcrumb">📁 Root Folder</div>`;
    }

    if (filteredFiles.length === 0) {
        container.innerHTML = breadcrumb + '<p class="no-data">No files found</p>';
        return;
    }

    container.innerHTML = breadcrumb + filteredFiles.map(renderFileItem).join('');
}

// Render single file item
function renderFileItem(file) {
    // Handle folders
    if (file.type === 'folder') {
        const escapedPath = file.path.replace(/\\/g, '\\\\').replace(/'/g, "\\'");
        return `
            <div class="file-item folder-item">
                <div class="file-icon" onclick="loadFiles('${escapedPath}')" style="cursor: pointer;">📁</div>
                <div class="file-info" onclick="loadFiles('${escapedPath}')" style="cursor: pointer;">
                    <div class="file-name">${file.name}</div>
                    <div class="file-meta">${file.video_count} videos • ${file.subtitle_count} subtitles</div>
                </div>
                <div class="file-actions">
                    <button onclick="loadFiles('${escapedPath}'); event.stopPropagation();" class="btn-secondary">➡️ Open</button>
                    <button onclick="openMoveModal('${escapedPath}', 'folder'); event.stopPropagation();" class="btn-secondary">📦 Move</button>
                    <button onclick="deleteItem('${escapedPath}', 'folder'); event.stopPropagation();" class="btn-secondary" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">🗑️ Delete</button>
                </div>
            </div>
        `;
    }

    // Handle files
    const icon = getFileIcon(file.type);
    const size = formatFileSize(file.size);

    // Check if file is a video
    const isVideo = ['.mp4', '.mkv', '.avi', '.webm', '.mov'].includes(file.type);

    // Check if file is a subtitle
    const isSubtitle = ['.srt', '.vtt', '.ass'].includes(file.type);

    // Subtitle language badges
    let subtitleBadges = '';
    if (isVideo && file.has_subtitles && file.subtitle_languages) {
        subtitleBadges = file.subtitle_languages.map(lang => {
            const langDisplay = lang === 'default' ? 'SUB' : lang.toUpperCase();
            const langTitle = lang === 'default' ? 'Subtitle available' : `Subtitle: ${lang.toUpperCase()}`;
            return `<span class="subtitle-badge subtitle-lang-badge" title="${langTitle}">${langDisplay}</span>`;
        }).join(' ');
    }

    // Escape single quotes and backslashes for onclick handlers
    const escapedPath = file.path.replace(/\\/g, '\\\\').replace(/'/g, "\\'");

    // Build action buttons - Main button + context menu for auxiliary actions
    let actionButtons = '';
    let contextMenuItems = [];

    if (isVideo) {
        // Main Play button (always visible)
        actionButtons += `<button onclick="playVideo('${escapedPath}')" class="btn-play">▶️ Play</button>`;

        // Context menu items for videos
        if (file.type !== '.mp4') {
            contextMenuItems.push({
                label: '🔄 Convert to MP4',
                action: `transcodeToMP4('${escapedPath}')`,
                title: 'Convert to MP4 format'
            });
        }

        if (!file.has_subtitles) {
            contextMenuItems.push({
                label: '🎙️ Generate Subtitles',
                action: `generateSubtitles('${escapedPath}')`,
                title: 'Generate subtitles using Whisper'
            });
        } else {
            const srtPath = file.path.replace(/\.(mp4|mkv|avi|webm|mov)$/i, '.srt');
            contextMenuItems.push({
                label: '✨ Clean Subtitles',
                action: `cleanSubtitles('${srtPath.replace(/\\/g, '\\\\').replace(/'/g, "\\'")}')`
,
                title: 'Apply hallucination filters'
            });
        }

        // Translate buttons for video's subtitles
        if (file.has_subtitles && file.subtitle_languages) {
            file.subtitle_languages.forEach(lang => {
                const langSrtPath = file.path.replace(/\.(mp4|mkv|avi|webm|mov)$/i, `.${lang}.srt`);
                const escapedLangSrt = langSrtPath.replace(/\\/g, '\\\\').replace(/'/g, "\\'");
                const langDisplay = lang === 'default' ? 'SUB' : lang.toUpperCase();
                contextMenuItems.push({
                    label: `🌐 Translate ${langDisplay}`,
                    action: `openTranslateDialog('${escapedLangSrt}')`,
                    title: `Translate ${langDisplay} subtitle`
                });
            });
        }

        // Download options
        contextMenuItems.push({
            label: '⬇️ Download Video',
            action: `downloadFile('${escapedPath}')`,
            title: 'Download video file'
        });

        if (file.has_subtitles) {
            const subtitleLang = file.subtitle_languages && file.subtitle_languages[0];
            const srtPath = subtitleLang === 'default'
                ? file.path.replace(/\.(mp4|mkv|avi|webm|mov)$/i, '.srt')
                : file.path.replace(/\.(mp4|mkv|avi|webm|mov)$/i, `.${subtitleLang}.srt`);
            const escapedSrtPath = srtPath.replace(/\\/g, '\\\\').replace(/'/g, "\\'");
            contextMenuItems.push({
                label: '⬇️ Download Subtitle',
                action: `downloadFile('${escapedSrtPath}')`,
                title: `Download subtitle file (${subtitleLang})`
            });
        }

        // Move and Delete
        contextMenuItems.push({
            label: '📦 Move',
            action: `openMoveModal('${escapedPath}', 'file')`,
            title: 'Move to another folder'
        });

        contextMenuItems.push({
            label: '🗑️ Delete Video',
            action: `deleteItem('${escapedPath}', 'file')`,
            title: 'Delete video file',
            danger: true
        });

        if (file.has_subtitles) {
            if (file.subtitle_languages && file.subtitle_languages.length > 1) {
                const subtitlesJson = JSON.stringify(file.subtitle_languages);
                const dataAttr = `data-subtitles='${subtitlesJson.replace(/'/g, "&apos;")}'`;
                contextMenuItems.push({
                    label: '🗑️ Delete Subtitle',
                    action: `deleteSubtitleWithSelection('${escapedPath}', event.target.closest('.context-menu-item'))`,
                    title: 'Delete subtitle file',
                    dataAttr: dataAttr,
                    danger: true
                });
            } else {
                const subtitleLang = file.subtitle_languages && file.subtitle_languages[0];
                const srtPath = subtitleLang === 'default'
                    ? file.path.replace(/\.(mp4|mkv|avi|webm|mov)$/i, '.srt')
                    : file.path.replace(/\.(mp4|mkv|avi|webm|mov)$/i, `.${subtitleLang}.srt`);
                const escapedSrtPath = srtPath.replace(/\\/g, '\\\\').replace(/'/g, "\\'");
                contextMenuItems.push({
                    label: '🗑️ Delete Subtitle',
                    action: `deleteItem('${escapedSrtPath}', 'file')`,
                    title: `Delete subtitle file (${subtitleLang})`,
                    danger: true
                });
            }
        }
    }

    if (isSubtitle) {
        // For standalone subtitle files
        actionButtons += `<button onclick="openTranslateDialog('${escapedPath}')" class="btn-play">🌐 Translate</button>`;

        contextMenuItems.push({
            label: '✨ Clean',
            action: `cleanSubtitles('${escapedPath}')`,
            title: 'Apply hallucination filters'
        });

        contextMenuItems.push({
            label: '⬇️ Download',
            action: `downloadFile('${escapedPath}')`,
            title: 'Download subtitle file'
        });

        contextMenuItems.push({
            label: '📦 Move',
            action: `openMoveModal('${escapedPath}', 'file')`,
            title: 'Move to another folder'
        });

        contextMenuItems.push({
            label: '🗑️ Delete',
            action: `deleteItem('${escapedPath}', 'file')`,
            title: 'Delete file',
            danger: true
        });
    }

    // If not video or subtitle, just show download/move/delete in menu
    if (!isVideo && !isSubtitle) {
        contextMenuItems.push({
            label: '⬇️ Download',
            action: `downloadFile('${escapedPath}')`,
            title: 'Download file'
        });

        contextMenuItems.push({
            label: '📦 Move',
            action: `openMoveModal('${escapedPath}', 'file')`,
            title: 'Move to another folder'
        });

        contextMenuItems.push({
            label: '🗑️ Delete',
            action: `deleteItem('${escapedPath}', 'file')`,
            title: 'Delete file',
            danger: true
        });
    }

    // Build context menu HTML
    if (contextMenuItems.length > 0) {
        const menuId = `menu-${file.name.replace(/[^a-zA-Z0-9]/g, '_')}`;
        actionButtons += `
            <div class="context-menu-container">
                <button onclick="toggleContextMenu('${menuId}', event)" class="btn-secondary btn-context-menu" title="More actions">⋮ More</button>
                <div id="${menuId}" class="context-menu">
                    ${contextMenuItems.map((item, idx) => {
                        const dangerClass = item.danger ? 'context-menu-danger' : '';
                        const dataAttr = item.dataAttr || '';
                        return `<div class="context-menu-item ${dangerClass}" ${dataAttr} onclick="${item.action}; closeAllContextMenus();" title="${item.title || ''}">${item.label}</div>`;
                    }).join('')}
                </div>
            </div>
        `;
    }

    return `
        <div class="file-item">
            <div class="file-icon">${icon}</div>
            <div class="file-info">
                <div class="file-name">
                    ${file.name}
                    ${subtitleBadges}
                </div>
                <div class="file-meta">${size} • ${formatDate(file.modified)}</div>
            </div>
            <div class="file-actions">
                ${actionButtons}
            </div>
        </div>
    `;
}

// Context menu functions
function toggleContextMenu(menuId, event) {
    // Prevent event from bubbling to document click listener
    if (event) {
        event.stopPropagation();
    }

    // Close all other menus first
    document.querySelectorAll('.context-menu').forEach(menu => {
        if (menu.id !== menuId) {
            menu.classList.remove('show');
            menu.style.display = '';
            menu.style.visibility = '';
            menu.style.top = '';
            menu.style.left = '';

            // Restore to original parent
            if (menu._originalParent && menu.parentElement === document.body) {
                menu._originalParent.appendChild(menu);
            }
        }
    });

    // Toggle the clicked menu
    const menu = document.getElementById(menuId);
    if (!menu) {
        console.error('Menu not found:', menuId);
        return;
    }

    const isShowing = menu.classList.contains('show');

    if (!isShowing) {
        // Find the button that triggered this menu
        const button = menu.previousElementSibling; // The "⋮ More" button
        if (!button) {
            console.error('Button not found for menu:', menuId);
            return;
        }

        // IMPORTANT: Move menu to body to escape transform positioning context
        // The file-item has transform on hover which breaks position:fixed
        if (menu.parentElement.classList.contains('context-menu-container')) {
            menu._originalParent = menu.parentElement;
            document.body.appendChild(menu);
        }

        const buttonRect = button.getBoundingClientRect();
        const viewportHeight = window.innerHeight;
        const viewportWidth = window.innerWidth;

        // Measure menu dimensions by temporarily making it visible but hidden
        menu.style.visibility = 'hidden';
        menu.style.display = 'block';
        menu.style.position = 'fixed';
        menu.style.top = '0px';
        menu.style.left = '0px';

        const menuHeight = menu.offsetHeight;
        const menuWidth = menu.offsetWidth;

        // Calculate position - align menu with button vertically at button's top
        // Position to the left of button horizontally
        let top = buttonRect.top; // Button's top position relative to viewport
        let left = buttonRect.left - menuWidth - 5; // 5px gap to the left of button

        // Ensure menu stays within vertical viewport
        // If menu would extend below viewport, shift it up
        if (top + menuHeight > viewportHeight) {
            top = Math.max(10, viewportHeight - menuHeight - 10);
        }

        // Ensure menu doesn't go above viewport
        if (top < 10) {
            top = 10;
        }

        // Ensure menu stays within horizontal viewport bounds
        // Check if menu would go off left edge
        if (left < 10) {
            // Not enough space on left, position to the right of button instead
            left = buttonRect.right + 5;

            // If that goes off right edge too, align right edges
            if (left + menuWidth > viewportWidth - 10) {
                left = buttonRect.right - menuWidth; // Align right edges
            }
        }

        // Apply position and make visible
        menu.style.top = `${top}px`;
        menu.style.left = `${left}px`;
        menu.style.visibility = 'visible';
        menu.classList.add('show');
    } else {
        // Hide the menu
        menu.classList.remove('show');
        menu.style.display = '';
        menu.style.visibility = '';
        menu.style.top = '';
        menu.style.left = '';

        // Restore menu to its original parent
        if (menu._originalParent && menu.parentElement === document.body) {
            menu._originalParent.appendChild(menu);
        }
    }
}

function closeAllContextMenus() {
    document.querySelectorAll('.context-menu').forEach(menu => {
        menu.classList.remove('show');
        menu.style.display = '';
        menu.style.visibility = '';
        menu.style.top = '';
        menu.style.left = '';

        // Restore menu to its original parent if it was moved to body
        if (menu._originalParent && menu.parentElement === document.body) {
            menu._originalParent.appendChild(menu);
        }
    });
}

// Close context menus when clicking outside
document.addEventListener('click', function(e) {
    // Check if click is inside any context menu or a menu item
    const clickedMenu = e.target.closest('.context-menu');
    const clickedMenuItem = e.target.closest('.context-menu-item');
    const clickedButton = e.target.closest('.btn-context-menu');

    // If clicked outside menu, button, or if clicked a menu item, close all menus
    if (!clickedMenu && !clickedButton) {
        closeAllContextMenus();
    }
}, true); // Use capture phase to ensure we catch the event

// Download file
function downloadFile(path) {
    window.location.href = `/api/files/${encodeURIComponent(path)}?download=true`;
}

// Transcode video to MP4
async function transcodeToMP4(videoPath) {
    const fileName = videoPath.split('/').pop();
    const confirmed = await showConfirmModal(
        `Convert this video to MP4 format?\n\n${fileName}\n\nThis will create a new MP4 file with H.264 codec for better browser compatibility. The original file will be kept.`,
        '🔄 Convert to MP4',
        'Convert'
    );

    if (!confirmed) {
        return;
    }

    try {
        const response = await fetch('/api/transcode-to-mp4', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ file_path: videoPath })
        });

        const data = await response.json();

        if (response.ok) {
            showNotification(`✅ Transcoding job started! Job ID: ${data.job_id}`, 'success');

            // Switch to Jobs tab to show the new job
            switchMainTab('jobs');

            // Refresh jobs list to show the new transcode job
            setTimeout(() => loadJobs(), 500);

            // Refresh files after a delay
            setTimeout(() => loadFiles(currentFolderPath), 2000);
        } else {
            showNotification(`❌ ${data.error || 'Failed to start transcoding'}`, 'error');
        }
    } catch (error) {
        console.error('Transcoding error:', error);
        showNotification('❌ Failed to start transcoding', 'error');
    }
}

// Generate subtitles for existing video file
async function generateSubtitles(videoPath) {
    const confirmed = await showConfirmModal(
        `Generate subtitles for this video?\n\n${videoPath}\n\nThis will use the default settings from config.yaml.`,
        '🎙️ Generate Subtitles',
        'Generate'
    );

    if (!confirmed) {
        return;
    }

    try {
        showNotification('Starting subtitle generation...', 'success');

        const response = await fetch('/api/generate-subtitles', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ file_path: videoPath })
        });

        const data = await response.json();

        if (response.ok) {
            showNotification(`Subtitles generation started! Job ID: ${data.job_id}`, 'success');

            // Switch to Jobs tab to show the new job
            switchMainTab('jobs');

            // Refresh jobs list to show the new transcription job
            setTimeout(() => loadJobs(), 500);

            // Refresh files after a delay - stay in current folder
            setTimeout(() => loadFiles(currentFolderPath), 2000);
        } else {
            showNotification(data.error || 'Failed to generate subtitles', 'error');
        }
    } catch (error) {
        console.error('Generate subtitles error:', error);
        showNotification('Failed to generate subtitles', 'error');
    }
}

// Clean existing subtitle file with hallucination filters
async function cleanSubtitles(srtPath) {
    const confirmed = await showConfirmModal(
        `Clean this subtitle file with hallucination filters?\n\n${srtPath}\n\nThis will overwrite the original file.`,
        '✨ Clean Subtitles',
        'Clean'
    );

    if (!confirmed) {
        return;
    }

    try {
        showNotification('Cleaning subtitles...', 'success');

        const response = await fetch('/api/clean-subtitles', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ file_path: srtPath })
        });

        const data = await response.json();

        if (response.ok) {
            showNotification(`✨ Subtitles cleaned!\n${data.message}`, 'success');
            // Refresh files to update any metadata - stay in current folder
            setTimeout(() => loadFiles(currentFolderPath), 1000);
        } else {
            showNotification(data.error || 'Failed to clean subtitles', 'error');
        }
    } catch (error) {
        console.error('Clean subtitles error:', error);
        showNotification('Failed to clean subtitles', 'error');
    }
}

// Get file icon based on type
function getFileIcon(type) {
    const icons = {
        '.mp4': '🎬',
        '.mp3': '🎵',
        '.wav': '🎵',
        '.srt': '📄',
        '.txt': '📄',
        '.log': '📋'
    };
    return icons[type] || '📁';
}

// Format file size
function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

// Format date
function formatDate(isoString) {
    if (!isoString) return 'N/A';
    const date = new Date(isoString);
    return date.toLocaleString();
}

// Truncate URL
function truncateUrl(url, maxLength = 60) {
    if (url.length <= maxLength) return url;
    return url.substring(0, maxLength) + '...';
}

// Show notification
function showNotification(message, type = 'success') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.remove();
    }, 5000);
}

// Video Player Functions
let currentVideoPath = null;
let positionSaveInterval = null;

function playVideo(videoPath) {
    const modal = document.getElementById('videoModal');
    const video = document.getElementById('videoPlayer');
    const subtitleTrack = document.getElementById('subtitleTrack');
    const title = document.getElementById('videoTitle');

    // Store current video path
    currentVideoPath = videoPath;

    // Extract filename for title
    const fileName = videoPath.split('/').pop();
    title.textContent = fileName;

    // Check file format
    const fileExt = fileName.split('.').pop().toLowerCase();
    const browserCompatible = ['mp4', 'webm'].includes(fileExt);

    // If not browser-compatible, suggest conversion first
    if (!browserCompatible) {
        // Close current function and call async version
        playVideoWithConversionCheck(videoPath, fileName, fileExt);
        return;
    }

    // Use direct file endpoint (no transcoding to prevent server hanging)
    video.src = `/api/files/${encodeURIComponent(videoPath)}`;

    // Add error handler for video playback issues
    video.onerror = function() {
        showNotification(
            `❌ Cannot play this ${fileExt.toUpperCase()} file. Your browser doesn't support this format. ` +
            `Use "Convert to MP4" from the More (⋮) menu to create a browser-compatible file.`,
            'error'
        );
    };

    // Load subtitle preferences
    loadSubtitlePreferences();

    // Detect all available subtitle languages for this video
    detectSubtitleLanguages(videoPath);

    // Restore saved playback position
    video.addEventListener('loadedmetadata', function restorePosition() {
        const savedPosition = loadVideoPosition(videoPath);
        if (savedPosition > 0 && savedPosition < video.duration - 5) {
            video.currentTime = savedPosition;
            console.log(`Restored position: ${formatTime(savedPosition)} / ${formatTime(video.duration)}`);
        }
        video.removeEventListener('loadedmetadata', restorePosition);
    });

    // Remove old event listeners to prevent duplicates
    video.removeEventListener('timeupdate', saveCurrentPosition);
    if (video._endedHandler) {
        video.removeEventListener('ended', video._endedHandler);
    }

    // Save position periodically during playback
    video.addEventListener('timeupdate', saveCurrentPosition);

    // Clear saved position when video finishes
    video._endedHandler = function clearPosition() {
        if (currentVideoPath) {
            localStorage.removeItem(`video_position_${currentVideoPath}`);
            console.log('Video finished - cleared saved position');
        }
    };
    video.addEventListener('ended', video._endedHandler);

    // Show modal
    ModalManager.open(modal);

    // Auto-play
    video.play();
}

// Handle video playback with conversion check for non-MP4 files
async function playVideoWithConversionCheck(videoPath, fileName, fileExt) {
    // Show three-option dialog
    const conversionChoice = await showConversionOptionsModal(fileName, fileExt);

    if (conversionChoice === 'server') {
        // Server-side conversion
        const mp4Path = await convertAndPlay(videoPath, fileName);
        if (mp4Path) {
            playVideo(mp4Path);
        } else {
            showNotification('Conversion was cancelled or failed', 'error');
        }
    } else if (conversionChoice === 'client') {
        // Client-side conversion
        const mp4Blob = await transcodeClientSide(videoPath, fileName);
        if (mp4Blob) {
            // Play the transcoded blob
            playVideoFromBlob(mp4Blob, fileName);
        } else {
            showNotification('Client-side transcoding was cancelled or failed', 'error');
        }
    } else {
        // User wants to try playing anyway
        showNotification(
            `⚠️ Attempting to play ${fileExt.toUpperCase()} file. If it doesn't work, use "Convert to MP4" from the More (⋮) menu.`,
            'warning'
        );

        // Continue with normal playback
        const modal = document.getElementById('videoModal');
        const video = document.getElementById('videoPlayer');
        const subtitleTrack = document.getElementById('subtitleTrack');
        const title = document.getElementById('videoTitle');

        currentVideoPath = videoPath;
        title.textContent = fileName;

        video.src = `/api/files/${encodeURIComponent(videoPath)}`;

        video.onerror = function() {
            showNotification(
                `❌ Cannot play this ${fileExt.toUpperCase()} file. Use "Convert to MP4" from the More (⋮) menu.`,
                'error'
            );
        };

        loadSubtitlePreferences();
        detectSubtitleLanguages(videoPath);

        video.addEventListener('loadedmetadata', function restorePosition() {
            const savedPosition = loadVideoPosition(videoPath);
            if (savedPosition > 0 && savedPosition < video.duration - 5) {
                video.currentTime = savedPosition;
            }
            video.removeEventListener('loadedmetadata', restorePosition);
        });

        // Remove old event listeners to prevent duplicates
        video.removeEventListener('timeupdate', saveCurrentPosition);
        if (video._endedHandler) {
            video.removeEventListener('ended', video._endedHandler);
        }

        video.addEventListener('timeupdate', saveCurrentPosition);

        video._endedHandler = function clearPosition() {
            if (currentVideoPath) {
                localStorage.removeItem(`video_position_${currentVideoPath}`);
            }
        };
        video.addEventListener('ended', video._endedHandler);

        ModalManager.open(modal);
        video.play();
    }
}

// Convert video to MP4 and return the new file path
async function convertAndPlay(videoPath, fileName) {
    try {
        // Start the conversion
        const response = await fetch('/api/transcode-to-mp4', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ file_path: videoPath })
        });

        const data = await response.json();

        if (!response.ok) {
            showNotification(`❌ ${data.error || 'Conversion failed'}`, 'error');
            return null;
        }

        const jobId = data.job_id;

        showNotification(`🔄 Converting ${fileName} to MP4...`, 'info');

        // Monitor the job until completion
        return new Promise((resolve) => {
            const checkInterval = setInterval(async () => {
                // Check if job exists in jobs array
                const job = jobs.find(j => j.id === jobId);

                if (job) {
                    if (job.status === 'completed') {
                        clearInterval(checkInterval);
                        showNotification('✅ Conversion completed! Starting playback...', 'success');

                        // Return the MP4 path (original path with .mp4 extension)
                        const mp4Path = videoPath.replace(/\.[^/.]+$/, '.mp4');

                        // Refresh file list to show new MP4
                        loadFiles(currentFolderPath);

                        resolve(mp4Path);
                    } else if (job.status === 'failed' || job.status === 'cancelled') {
                        clearInterval(checkInterval);
                        showNotification(`❌ Conversion ${job.status}`, 'error');
                        resolve(null);
                    }
                    // If still running, keep checking
                }
            }, 1000); // Check every second

            // Timeout after 10 minutes
            setTimeout(() => {
                clearInterval(checkInterval);
                showNotification('❌ Conversion timeout', 'error');
                resolve(null);
            }, 600000);
        });
    } catch (error) {
        showNotification(`❌ Error starting conversion: ${error.message}`, 'error');
        return null;
    }
}

function saveCurrentPosition() {
    if (currentVideoPath) {
        const video = document.getElementById('videoPlayer');
        // Only save if video is playing and not at the very end
        if (!video.paused && video.currentTime > 1 && video.currentTime < video.duration - 5) {
            saveVideoPosition(currentVideoPath, video.currentTime);
        }
    }
}

function saveVideoPosition(videoPath, position) {
    try {
        localStorage.setItem(`video_position_${videoPath}`, position.toString());
    } catch (e) {
        console.warn('Failed to save video position:', e);
    }
}

function loadVideoPosition(videoPath) {
    try {
        const position = localStorage.getItem(`video_position_${videoPath}`);
        return position ? parseFloat(position) : 0;
    } catch (e) {
        console.warn('Failed to load video position:', e);
        return 0;
    }
}

function formatTime(seconds) {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    if (h > 0) {
        return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
    }
    return `${m}:${s.toString().padStart(2, '0')}`;
}

function closeVideoPlayer() {
    const modal = document.getElementById('videoModal');
    const video = document.getElementById('videoPlayer');

    // Save final position before closing (if not finished watching)
    if (currentVideoPath && video.currentTime > 1 && video.currentTime < video.duration - 5) {
        saveVideoPosition(currentVideoPath, video.currentTime);
        console.log(`Saved position: ${formatTime(video.currentTime)} / ${formatTime(video.duration)}`);
    }

    // Remove event listeners to prevent memory leaks
    video.removeEventListener('timeupdate', saveCurrentPosition);
    video.removeEventListener('ended', video._endedHandler);

    // Remove error handler to prevent error when clearing src
    video.onerror = null;

    // Pause and reset
    video.pause();
    video.currentTime = 0;
    video.src = '';

    // Clear current video path
    currentVideoPath = null;

    // Hide modal using ModalManager
    ModalManager.close(modal);
}

// Open translate dialog for currently playing video's subtitle
function translateVideoSubtitleFile() {
    if (!currentVideoPath) {
        showNotification('⚠️ No video is currently playing', 'error');
        return;
    }

    // Get the currently selected subtitle language
    const subtitleSelect = document.getElementById('subtitleLanguage');
    const selectedLang = subtitleSelect.value;

    if (!selectedLang) {
        showNotification('⚠️ No subtitle is currently selected', 'error');
        return;
    }

    // Construct subtitle file path
    const basePath = currentVideoPath.replace(/\.(mp4|mkv|avi|webm|mov)$/i, '');
    let srtPath;

    if (selectedLang === 'default') {
        srtPath = currentVideoPath.replace(/\.(mp4|mkv|avi|webm|mov)$/i, '.srt');
    } else {
        srtPath = `${basePath}.${selectedLang}.srt`;
    }

    // Open the translation dialog with this subtitle file
    openTranslateDialog(srtPath);
}

function changeSpeed(speed) {
    const video = document.getElementById('videoPlayer');
    video.playbackRate = speed;

    // Update button states
    document.querySelectorAll('.speed-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.textContent === `${speed}x`) {
            btn.classList.add('active');
        }
    });
}

// Subtitle customization functions
function changeSubtitleSize(size) {
    const videoContainer = document.querySelector('.video-container');

    // Remove all size classes
    videoContainer.classList.remove('subtitle-small', 'subtitle-medium', 'subtitle-large', 'subtitle-xlarge', 'subtitle-xxlarge', 'subtitle-xxxlarge');

    // Add new size class
    videoContainer.classList.add(`subtitle-${size}`);

    // Save preference
    setCookie('subtitle-size', size);

    // Update button states
    document.querySelectorAll('.subtitle-size-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.size === size) {
            btn.classList.add('active');
        }
    });
}

function changeSubtitleFont(font) {
    // Update CSS variable
    document.documentElement.style.setProperty('--subtitle-font', `'${font}', sans-serif`);

    // Save preference
    setCookie('subtitle-font', font);
}

function loadSubtitlePreferences() {
    // Load subtitle size
    const savedSize = getCookie('subtitle-size') || 'large';
    changeSubtitleSize(savedSize);

    // Load subtitle font
    const savedFont = getCookie('subtitle-font') || 'Inter';
    const fontSelect = document.getElementById('subtitleFont');
    if (fontSelect) {
        fontSelect.value = savedFont;
        changeSubtitleFont(savedFont);
    }
}

// Convert SRT to VTT format for HTML5 video
async function convertSrtToVtt(srtPath) {
    const response = await fetch(`/api/files/${encodeURIComponent(srtPath)}`);
    const srtText = await response.text();

    // Simple SRT to VTT conversion
    let vttText = 'WEBVTT\n\n';

    // Replace commas with periods in timestamps (SRT uses comma, VTT uses period)
    vttText += srtText.replace(/(\d{2}:\d{2}:\d{2}),(\d{3})/g, '$1.$2');

    return new Blob([vttText], { type: 'text/vtt' });
}

// Filter Editor Functions
async function openFilterEditor() {
    // Load current filters from server
    try {
        const response = await fetch('/api/filters');
        const filters = await response.json();
        currentFilters = filters;
    } catch (error) {
        console.error('Failed to load filters:', error);
        // Use defaults if API fails
        currentFilters = {
            bad_phrases: [],
            bad_patterns: []
        };
    }

    // Render filter lists
    renderFilterLists();

    // Show modal
    ModalManager.open(document.getElementById("filterModal"));
}

function closeFilterEditor() {
    ModalManager.close(document.getElementById("filterModal"));
}

function renderFilterLists() {
    // Render bad phrases
    const badPhrasesList = document.getElementById('badPhrasesList');
    if (currentFilters.bad_phrases && currentFilters.bad_phrases.length > 0) {
        badPhrasesList.innerHTML = currentFilters.bad_phrases.map((phrase, index) => `
            <div class="filter-item">
                <span class="filter-text">${phrase}</span>
                <button onclick="removeBadPhrase(${index})" class="btn-filter-remove">✕</button>
            </div>
        `).join('');
    } else {
        badPhrasesList.innerHTML = '<p class="no-data">No bad phrases defined</p>';
    }

    // Render bad patterns
    const badPatternsList = document.getElementById('badPatternsList');
    if (currentFilters.bad_patterns && currentFilters.bad_patterns.length > 0) {
        badPatternsList.innerHTML = currentFilters.bad_patterns.map((pattern, index) => `
            <div class="filter-item">
                <span class="filter-text"><code>${pattern}</code></span>
                <button onclick="removeBadPattern(${index})" class="btn-filter-remove">✕</button>
            </div>
        `).join('');
    } else {
        badPatternsList.innerHTML = '<p class="no-data">No patterns defined</p>';
    }
}

function addBadPhrase() {
    const input = document.getElementById('newBadPhrase');
    const phrase = input.value.trim();

    if (phrase) {
        if (!currentFilters.bad_phrases) {
            currentFilters.bad_phrases = [];
        }
        currentFilters.bad_phrases.push(phrase);
        input.value = '';
        renderFilterLists();
        showNotification(`Added phrase: "${phrase}"`, 'success');
    }
}

function removeBadPhrase(index) {
    const removed = currentFilters.bad_phrases.splice(index, 1);
    renderFilterLists();
    showNotification(`Removed phrase: "${removed[0]}"`, 'success');
}

function addBadPattern() {
    const input = document.getElementById('newBadPattern');
    const pattern = input.value.trim();

    if (pattern) {
        // Validate regex
        try {
            new RegExp(pattern);
            if (!currentFilters.bad_patterns) {
                currentFilters.bad_patterns = [];
            }
            currentFilters.bad_patterns.push(pattern);
            input.value = '';
            renderFilterLists();
            showNotification(`Added pattern: "${pattern}"`, 'success');
        } catch (e) {
            showNotification('Invalid regex pattern', 'error');
        }
    }
}

function removeBadPattern(index) {
    const removed = currentFilters.bad_patterns.splice(index, 1);
    renderFilterLists();
    showNotification(`Removed pattern: "${removed[0]}"`, 'success');
}

function testFilters() {
    const testText = document.getElementById('testText').value;
    const resultDiv = document.getElementById('testResult');

    if (!testText.trim()) {
        resultDiv.innerHTML = '<p class="error">Please enter some text to test</p>';
        return;
    }

    let matches = [];

    // Test bad phrases
    if (currentFilters.bad_phrases) {
        currentFilters.bad_phrases.forEach(phrase => {
            if (testText.toLowerCase().includes(phrase.toLowerCase())) {
                matches.push(`Phrase: "${phrase}"`);
            }
        });
    }

    // Test bad patterns
    if (currentFilters.bad_patterns) {
        currentFilters.bad_patterns.forEach(pattern => {
            try {
                const regex = new RegExp(pattern, 'gi');
                if (regex.test(testText)) {
                    matches.push(`Pattern: "${pattern}"`);
                }
            } catch (e) {
                // Skip invalid patterns
            }
        });
    }

    if (matches.length > 0) {
        resultDiv.innerHTML = `
            <div class="test-matches">
                <p class="test-title">✓ Found ${matches.length} match(es):</p>
                ${matches.map(m => `<div class="match-item">${m}</div>`).join('')}
            </div>
        `;
    } else {
        resultDiv.innerHTML = '<p class="test-no-match">No matches found - text would pass filters</p>';
    }
}

async function saveFilters() {
    try {
        const response = await fetch('/api/filters', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(currentFilters)
        });

        if (response.ok) {
            showNotification('Filters saved successfully!', 'success');
        } else {
            throw new Error('Failed to save filters');
        }
    } catch (error) {
        console.error('Failed to save filters:', error);
        showNotification('Failed to save filters', 'error');
    }
}

function exportFilters() {
    const dataStr = JSON.stringify(currentFilters, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);

    const link = document.createElement('a');
    link.href = url;
    link.download = 'whisper-filters.json';
    link.click();

    URL.revokeObjectURL(url);
    showNotification('Filters exported successfully!', 'success');
}

function importFilters(event) {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
        try {
            const imported = JSON.parse(e.target.result);

            // Validate structure
            if (!imported.bad_phrases && !imported.bad_patterns) {
                throw new Error('Invalid filter file format');
            }

            currentFilters = imported;
            renderFilterLists();
            showNotification('Filters imported successfully!', 'success');
        } catch (error) {
            console.error('Import error:', error);
            showNotification('Failed to import filters', 'error');
        }
    };

    reader.readAsText(file);
    event.target.value = ''; // Reset input
}

// Upload Modal Functions
let selectedUploadFiles = [];

function openUploadModal() {
    const modal = document.getElementById('uploadModal');
    const uploadInput = document.getElementById('uploadFiles');
    const uploadButton = document.getElementById('uploadButton');
    const uploadFileList = document.getElementById('uploadFileList');
    const uploadProgress = document.getElementById('uploadProgress');
    const dropZone = document.getElementById('uploadDropZone');

    // Reset state
    selectedUploadFiles = [];
    uploadInput.value = '';
    uploadButton.disabled = true;
    uploadFileList.style.display = 'none';
    uploadFileList.innerHTML = '';
    uploadProgress.style.display = 'none';
    document.getElementById('uploadDropContent').style.display = 'flex';

    // Setup file input change handler
    uploadInput.addEventListener('change', handleUploadFileSelect);

    // Setup drag and drop
    dropZone.addEventListener('dragover', handleUploadDragOver);
    dropZone.addEventListener('dragleave', handleUploadDragLeave);
    dropZone.addEventListener('drop', handleUploadDrop);

    ModalManager.open(modal);
}

function closeUploadModal() {
    const modal = document.getElementById('uploadModal');
    ModalManager.close(modal);
    selectedUploadFiles = [];
}

function handleUploadFileSelect(e) {
    const files = Array.from(e.target.files);
    selectedUploadFiles = files;
    displaySelectedUploadFiles(files);
}

function handleUploadDragOver(e) {
    e.preventDefault();
    e.stopPropagation();
    e.currentTarget.classList.add('drag-over');
}

function handleUploadDragLeave(e) {
    e.preventDefault();
    e.stopPropagation();
    e.currentTarget.classList.remove('drag-over');
}

function handleUploadDrop(e) {
    e.preventDefault();
    e.stopPropagation();
    e.currentTarget.classList.remove('drag-over');

    const files = Array.from(e.dataTransfer.files);
    selectedUploadFiles = files;

    // Update the file input
    const uploadInput = document.getElementById('uploadFiles');
    uploadInput.files = e.dataTransfer.files;

    displaySelectedUploadFiles(files);
}

function displaySelectedUploadFiles(files) {
    const uploadFileList = document.getElementById('uploadFileList');
    const uploadButton = document.getElementById('uploadButton');
    const dropContent = document.getElementById('uploadDropContent');

    if (files.length === 0) {
        uploadFileList.style.display = 'none';
        dropContent.style.display = 'flex';
        uploadButton.disabled = true;
        return;
    }

    dropContent.style.display = 'none';
    uploadFileList.style.display = 'block';
    uploadButton.disabled = false;

    uploadFileList.innerHTML = `
        <div style="padding: 20px; background: rgba(102, 126, 234, 0.1); border-radius: 12px;">
            <h3 style="margin-bottom: 15px; color: var(--text-primary);">${files.length} file(s) selected</h3>
            ${files.map((file, index) => `
                <div style="display: flex; justify-content: space-between; padding: 10px; background: rgba(255,255,255,0.05); border-radius: 8px; margin-bottom: 8px;">
                    <div>
                        <strong>${file.name}</strong>
                        <span style="color: var(--text-muted); margin-left: 10px;">${formatFileSize(file.size)}</span>
                    </div>
                    <button onclick="removeUploadFile(${index})" style="background: none; border: none; color: var(--text-primary); cursor: pointer; font-size: 1.2rem;" title="Remove">✕</button>
                </div>
            `).join('')}
        </div>
    `;
}

function removeUploadFile(index) {
    selectedUploadFiles.splice(index, 1);
    displaySelectedUploadFiles(selectedUploadFiles);
}

// Upload a file with progress tracking
function uploadFileWithProgress(formData, fileName, onProgress) {
    return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();

        // Track upload progress
        xhr.upload.addEventListener('progress', (e) => {
            if (e.lengthComputable) {
                const percentComplete = Math.round((e.loaded / e.total) * 100);
                onProgress(percentComplete);
            }
        });

        // Handle completion
        xhr.addEventListener('load', () => {
            try {
                const data = JSON.parse(xhr.responseText);
                if (xhr.status >= 200 && xhr.status < 300) {
                    resolve({ success: true, data });
                } else {
                    resolve({ success: false, error: data.error || `HTTP ${xhr.status}` });
                }
            } catch (error) {
                resolve({ success: false, error: 'Invalid server response' });
            }
        });

        // Handle errors
        xhr.addEventListener('error', () => {
            reject(new Error('Network error during upload'));
        });

        xhr.addEventListener('abort', () => {
            reject(new Error('Upload cancelled'));
        });

        // Send request
        xhr.open('POST', '/api/upload-file');
        xhr.send(formData);
    });
}

async function startUpload() {
    if (selectedUploadFiles.length === 0) {
        showNotification('No files selected', 'error');
        return;
    }

    const uploadButton = document.getElementById('uploadButton');
    const uploadProgress = document.getElementById('uploadProgress');
    const uploadProgressBar = document.getElementById('uploadProgressBar');
    const uploadStatus = document.getElementById('uploadStatus');

    // Disable upload button and show progress
    uploadButton.disabled = true;
    uploadProgress.style.display = 'block';

    let successCount = 0;
    let failCount = 0;
    const errors = [];

    for (let i = 0; i < selectedUploadFiles.length; i++) {
        const file = selectedUploadFiles[i];

        try {
            const formData = new FormData();
            formData.append('file', file);

            // Add current folder path if we're in a subfolder
            if (currentFolderPath) {
                formData.append('target_folder', currentFolderPath);
            }

            // Upload with progress tracking using XMLHttpRequest
            const result = await uploadFileWithProgress(formData, file.name, (progress) => {
                // Calculate overall progress: completed files + current file progress
                const completedProgress = (i / selectedUploadFiles.length) * 100;
                const currentProgress = (progress / selectedUploadFiles.length);
                const totalProgress = Math.round(completedProgress + currentProgress);

                uploadStatus.textContent = `Uploading ${file.name} (${i + 1}/${selectedUploadFiles.length}): ${progress}%`;
                uploadProgressBar.style.width = `${totalProgress}%`;
            });

            if (result.success) {
                successCount++;
                console.log(`✓ Uploaded ${file.name} to ${result.data.path}`);
            } else {
                failCount++;
                const errorMsg = result.error || 'Unknown error';
                errors.push(`${file.name}: ${errorMsg}`);
                console.error(`✗ Failed to upload ${file.name}:`, errorMsg);
            }
        } catch (error) {
            failCount++;
            errors.push(`${file.name}: ${error.message}`);
            console.error(`✗ Error uploading ${file.name}:`, error);
        }
    }

    // Show completion message
    uploadProgressBar.style.width = '100%';
    uploadStatus.textContent = `Upload complete! Success: ${successCount}, Failed: ${failCount}`;

    // Refresh file list - reload current folder
    setTimeout(() => loadFiles(currentFolderPath), 1000);

    // Show detailed notification
    if (failCount === 0) {
        showNotification(`Successfully uploaded ${successCount} file(s)!`, 'success');
    } else {
        // Show first error as example
        const errorSummary = errors.length > 0 ? `\n\nFirst error: ${errors[0]}` : '';
        showNotification(`Uploaded ${successCount} file(s), ${failCount} failed.${errorSummary}`, 'error');

        // Log all errors to console for debugging
        console.error('Upload errors:', errors);
    }

    // Close modal after short delay
    setTimeout(() => {
        closeUploadModal();
    }, 2000);
}

// Restart a job
async function restartJob(jobId) {
    const confirmed = await showConfirmModal(
        'Restart this job with the same settings?\n\nThis will create a new transcription job.',
        '🔄 Restart Job',
        'Restart'
    );

    if (!confirmed) {
        return;
    }

    try {
        const response = await fetch(`/api/jobs/${jobId}/restart`, {
            method: 'POST'
        });

        const data = await response.json();

        if (response.ok) {
            showNotification(`Job restarted! New Job ID: ${data.new_job_id}`, 'success');
            closeModal();
            loadJobs(); // Refresh job list
        } else {
            showNotification(data.error || 'Failed to restart job', 'error');
        }
    } catch (error) {
        console.error('Restart job error:', error);
        showNotification('Failed to restart job', 'error');
    }
}

// Cancel a running or queued job
async function cancelJob(jobId) {
    const confirmed = await showConfirmModal(
        'Stop this job?\n\nThe job will be cancelled and marked as incomplete.',
        '⏹️ Stop Job',
        'Stop'
    );

    if (!confirmed) {
        return;
    }

    try {
        const response = await fetch(`/api/jobs/${jobId}/cancel`, {
            method: 'POST'
        });

        const data = await response.json();

        if (response.ok) {
            showNotification('Job cancelled successfully', 'success');
            closeModal();
            loadJobs(); // Refresh job list
        } else {
            showNotification(data.error || 'Failed to cancel job', 'error');
        }
    } catch (error) {
        console.error('Cancel job error:', error);
        showNotification('Failed to cancel job', 'error');
    }
}

// Delete a job from the database
async function deleteJob(jobId) {
    const confirmed = await showConfirmModal(
        'Delete this job?\n\nThis will permanently remove the job from the database.\nThis action cannot be undone.',
        '🗑️ Delete Job',
        'Delete'
    );

    if (!confirmed) {
        return;
    }

    try {
        const response = await fetch(`/api/jobs/${jobId}/delete`, {
            method: 'POST'
        });

        const data = await response.json();

        if (response.ok) {
            showNotification('Job deleted successfully', 'success');
            closeModal();
            loadJobs(); // Refresh job list
        } else {
            showNotification(data.error || 'Failed to delete job', 'error');
        }
    } catch (error) {
        console.error('Delete job error:', error);
        showNotification('Failed to delete job', 'error');
    }
}

// Clear completed and failed jobs
async function clearCompletedFailedJobs() {
    const confirmed = await showConfirmModal(
        'Clear all completed and failed jobs from history?\n\nThis action cannot be undone.',
        '🧹 Clear Jobs History',
        'Clear'
    );

    if (!confirmed) {
        return;
    }

    try {
        const response = await fetch('/api/jobs/clear', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ statuses: ['completed', 'failed', 'cancelled'] })
        });

        const data = await response.json();

        if (response.ok) {
            showNotification(`Cleared ${data.deleted} job(s)`, 'success');
            // Immediately update local state
            jobs = jobs.filter(j => !['completed', 'failed', 'cancelled'].includes(j.status));
            renderJobs();
            // Also refresh from server to be sure
            await loadJobs();
        } else {
            showNotification(data.error || 'Failed to clear jobs', 'error');
        }
    } catch (error) {
        console.error('Clear jobs error:', error);
        showNotification('Failed to clear jobs', 'error');
    }
}

// ============================================================================
// File Management Functions
// ============================================================================

// Store current item being moved
let currentMoveItem = null;

// Open Create Folder Modal
function openCreateFolderModal() {
    document.getElementById('newFolderName').value = '';
    ModalManager.open(document.getElementById("createFolderModal"));
}

// Close Create Folder Modal
function closeCreateFolderModal() {
    ModalManager.close(document.getElementById("createFolderModal"));
}

// Create New Folder
async function createNewFolder() {
    const folderName = document.getElementById('newFolderName').value.trim();

    if (!folderName) {
        showNotification('Please enter a folder name', 'error');
        return;
    }

    try {
        const response = await fetch('/api/files/create-folder', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                folder_name: folderName,
                parent_path: currentFolderPath || ''
            })
        });

        const data = await response.json();

        if (response.ok) {
            showNotification(`Folder "${folderName}" created successfully`, 'success');
            closeCreateFolderModal();
            loadFiles(currentFolderPath);
        } else {
            showNotification(data.error || 'Failed to create folder', 'error');
        }
    } catch (error) {
        console.error('Create folder error:', error);
        showNotification('Failed to create folder', 'error');
    }
}

// Open Move Modal
async function openMoveModal(itemPath, itemType) {
    currentMoveItem = { path: itemPath, type: itemType };

    // Set item name in modal
    document.getElementById('moveItemPath').textContent = itemPath;

    // Fetch folder list
    try {
        const response = await fetch('/api/files/folders');
        const data = await response.json();

        const select = document.getElementById('moveDestination');
        select.innerHTML = '<option value="">/ (Root)</option>';

        if (data.folders) {
            data.folders.forEach(folder => {
                // Don't show the item itself if it's a folder
                if (itemType === 'folder' && folder.path === itemPath) {
                    return;
                }
                // Don't show subfolders of the item being moved
                if (itemType === 'folder' && folder.path.startsWith(itemPath + '/')) {
                    return;
                }

                const option = document.createElement('option');
                option.value = folder.path;
                option.textContent = folder.path;
                select.appendChild(option);
            });
        }

        ModalManager.open(document.getElementById("moveModal"));
    } catch (error) {
        console.error('Failed to load folders:', error);
        showNotification('Failed to load folder list', 'error');
    }
}

// Close Move Modal
function closeMoveModal() {
    ModalManager.close(document.getElementById("moveModal"));
    currentMoveItem = null;
}

// Confirm Move
async function confirmMove() {
    if (!currentMoveItem) {
        return;
    }

    const destination = document.getElementById('moveDestination').value;

    try {
        const response = await fetch('/api/files/move', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                source_path: currentMoveItem.path,
                destination_path: destination,
                item_type: currentMoveItem.type
            })
        });

        const data = await response.json();

        if (response.ok) {
            showNotification(`Successfully moved to ${destination || 'root'}`, 'success');
            closeMoveModal();
            loadFiles(currentFolderPath);
        } else {
            showNotification(data.error || 'Failed to move item', 'error');
        }
    } catch (error) {
        console.error('Move error:', error);
        showNotification('Failed to move item', 'error');
    }
}

// Global confirmation modal state
let confirmModalResolve = null;

// Show confirmation modal
function showConfirmModal(message, title = '⚠️ Confirm Action', confirmButtonText = 'Confirm') {
    return new Promise((resolve) => {
        confirmModalResolve = resolve;

        document.getElementById('confirmTitle').textContent = title;
        document.getElementById('confirmMessage').textContent = message;
        document.getElementById('confirmButton').textContent = confirmButtonText;
        ModalManager.open(document.getElementById("confirmModal"));
    });
}

// Close confirmation modal
function closeConfirmModal(confirmed) {
    // Resolve promise FIRST to ensure callbacks run before modal closes
    if (confirmModalResolve) {
        confirmModalResolve(confirmed);
        confirmModalResolve = null;
    }

    // Then close the modal UI
    ModalManager.close(document.getElementById("confirmModal"));
}

// Delete subtitle with language selection (for videos with multiple subtitles)
async function deleteSubtitleWithSelection(videoPath, buttonElement) {
    try {
        const subtitlesJson = buttonElement.getAttribute('data-subtitles');
        const subtitleLanguages = JSON.parse(subtitlesJson);

        // Create selection dialog
        const options = subtitleLanguages.map((lang, index) => {
            const langDisplay = lang === 'default' ? 'Default' : lang.toUpperCase();
            return `
                <label style="display: flex; align-items: center; padding: 10px; cursor: pointer; background: rgba(255,255,255,0.05); border-radius: 8px; margin-bottom: 8px;">
                    <input type="radio" name="subtitle-lang" value="${lang}" ${index === 0 ? 'checked' : ''} style="margin-right: 10px;">
                    <span style="font-size: 1.1rem;">${langDisplay} (${videoPath.replace(/\.(mp4|mkv|avi|webm|mov)$/i, `.${lang}.srt`).split('/').pop()})</span>
                </label>
            `;
        }).join('');

        // Show custom dialog
        const dialogHtml = `
            <div style="text-align: left;">
                <p style="margin-bottom: 15px;">Select which subtitle to delete:</p>
                <div id="subtitle-selection">
                    ${options}
                </div>
            </div>
        `;

        const modal = document.getElementById('confirmModal');
        const message = modal.querySelector('.modal-message');
        const title = modal.querySelector('.modal-title');
        const confirmBtn = modal.querySelector('.modal-confirm');
        const cancelBtn = modal.querySelector('.modal-cancel');

        title.textContent = '🗑️ Delete Subtitle';
        message.innerHTML = dialogHtml;
        confirmBtn.textContent = 'Delete';
        modal.classList.add('show');

        // Wait for user choice
        const result = await new Promise((resolve) => {
            const handleConfirm = () => {
                const selected = document.querySelector('input[name="subtitle-lang"]:checked');
                cleanup();
                resolve(selected ? selected.value : null);
            };

            const handleCancel = () => {
                cleanup();
                resolve(null);
            };

            const cleanup = () => {
                confirmBtn.removeEventListener('click', handleConfirm);
                cancelBtn.removeEventListener('click', handleCancel);
                modal.classList.remove('show');
            };

            confirmBtn.addEventListener('click', handleConfirm);
            cancelBtn.addEventListener('click', handleCancel);
        });

        if (result) {
            // Construct subtitle path
            const srtPath = result === 'default'
                ? videoPath.replace(/\.(mp4|mkv|avi|webm|mov)$/i, '.srt')
                : videoPath.replace(/\.(mp4|mkv|avi|webm|mov)$/i, `.${result}.srt`);

            // Delete the selected subtitle
            await deleteItem(srtPath, 'file');
        }
    } catch (error) {
        console.error('Error in deleteSubtitleWithSelection:', error);
        showNotification('Failed to delete subtitle', 'error');
    }
}

// Delete Item (file or folder)
async function deleteItem(itemPath, itemType) {
    const itemTypeName = itemType === 'folder' ? 'folder' : 'file';
    const itemName = itemPath.split('/').pop() || itemPath;

    const confirmed = await showConfirmModal(
        `Are you sure you want to delete this ${itemTypeName}?\n\n${itemName}\n\nThis action cannot be undone.`,
        '🗑️ Delete ' + itemTypeName.charAt(0).toUpperCase() + itemTypeName.slice(1),
        'Delete'
    );

    if (!confirmed) {
        return;
    }

    try {
        const response = await fetch('/api/files/delete', {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                path: itemPath,
                item_type: itemType
            })
        });

        const data = await response.json();

        if (response.ok) {
            showNotification(`${itemTypeName.charAt(0).toUpperCase() + itemTypeName.slice(1)} deleted successfully`, 'success');
            loadFiles(currentFolderPath);
        } else if (response.status === 423) {
            // File is locked (in use)
            const retry = await showConfirmModal(
                `${data.error}\n\nThis usually happens if a transcription job just completed.\n\nWould you like to wait 2 seconds and retry?`,
                '⏳ File In Use',
                'Retry'
            );

            if (retry) {
                // Wait 2 seconds and retry
                await new Promise(resolve => setTimeout(resolve, 2000));
                showNotification('Retrying deletion...', 'info');
                // Recursive retry
                await deleteItem(itemPath, itemType);
            }
        } else {
            showNotification(data.error || `Failed to delete ${itemTypeName}`, 'error');
        }
    } catch (error) {
        console.error('Delete error:', error);
        showNotification(`Failed to delete ${itemTypeName}`, 'error');
    }
}

// ==========================================
// Translation Functions
// ==========================================

let currentTranslateFilePath = '';

// Open translation dialog
function openTranslateDialog(filePath) {
    currentTranslateFilePath = filePath;

    const fileName = filePath.split('/').pop();
    document.getElementById('translateFileName').textContent = `File: ${fileName}`;

    // Try to detect source language from filename
    // e.g., "video.sr.srt" -> source is "sr", "video.rus.srt" -> source is "rus"
    const parts = fileName.split('.');
    const sourceLangSelect = document.getElementById('translateSourceLang');

    // Reset to auto-detect by default
    sourceLangSelect.value = 'auto';

    // If file has language suffix pattern (e.g., video.sr.srt, video.rus.srt)
    if (parts.length >= 3 && parts[parts.length - 1] === 'srt') {
        const possibleLang = parts[parts.length - 2].toLowerCase();
        // Check if it's a valid 2 or 3-letter language code
        if ((possibleLang.length === 2 || possibleLang.length === 3) || possibleLang === 'auto') {
            // Try to find the language code in the dropdown
            const option = Array.from(sourceLangSelect.options).find(opt =>
                opt.value.toLowerCase() === possibleLang
            );
            if (option) {
                sourceLangSelect.value = option.value;
                console.log(`Auto-detected source language from filename: ${option.value} (${possibleLang})`);
            } else {
                // Map 3-letter codes to 2-letter codes
                const langMap = {
                    'rus': 'ru',  // Russian
                    'srp': 'sr',  // Serbian
                    'eng': 'en',  // English
                    'deu': 'de',  // German
                    'ger': 'de',  // German
                    'fra': 'fr',  // French
                    'fre': 'fr',  // French
                    'spa': 'es',  // Spanish
                    'ita': 'it',  // Italian
                    'por': 'pt',  // Portuguese
                    'pol': 'pl',  // Polish
                    'tur': 'tr',  // Turkish
                    'nld': 'nl',  // Dutch
                    'dut': 'nl',  // Dutch
                };

                const mappedLang = langMap[possibleLang];
                if (mappedLang) {
                    const mappedOption = Array.from(sourceLangSelect.options).find(opt =>
                        opt.value === mappedLang
                    );
                    if (mappedOption) {
                        sourceLangSelect.value = mappedLang;
                        console.log(`Auto-detected source language: ${mappedLang} (mapped from ${possibleLang})`);
                    }
                }
            }
        }
    }

    ModalManager.open(document.getElementById("translateModal"));
}

// Close translation dialog
function closeTranslateDialog() {
    ModalManager.close(document.getElementById("translateModal"));
    currentTranslateFilePath = '';
}

// Start translation job
async function startTranslation() {
    let sourceLang = document.getElementById('translateSourceLang').value;
    const targetLang = document.getElementById('translateTargetLang').value;

    // Normalize "default" to "auto"
    if (sourceLang === 'default' || !sourceLang) {
        sourceLang = 'auto';
    }

    if (sourceLang === targetLang && sourceLang !== 'auto') {
        showNotification('⚠️ Source and target languages are the same', 'error');
        return;
    }

    if (!currentTranslateFilePath) {
        showNotification('⚠️ No file selected', 'error');
        return;
    }

    try {
        const response = await fetch('/api/translate-subtitle', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                file_path: currentTranslateFilePath,
                source_lang: sourceLang,
                target_lang: targetLang
            })
        });

        const data = await response.json();

        if (response.ok) {
            showNotification(`✅ Translation job started! Job ID: ${data.job_id}`, 'success');
            closeTranslateDialog();
            // Refresh files after a delay
            setTimeout(() => loadFiles(currentFolderPath), 2000);
        } else {
            showNotification(`❌ ${data.error || 'Failed to start translation'}`, 'error');
        }
    } catch (error) {
        console.error('Translation error:', error);
        showNotification('❌ Failed to start translation', 'error');
    }
}

// Detect available subtitle languages for video
async function detectSubtitleLanguages(videoPath) {
    const baseName = videoPath.replace(/\.(mp4|mkv|avi|webm|mov)$/i, '');
    const languageSelect = document.getElementById('subtitleLanguage');
    const subtitleTrack = document.getElementById('subtitleTrack');

    // Clear existing options
    languageSelect.innerHTML = '<option value="">No subtitles</option>';

    // Get file list to check for language-suffixed SRTs
    const folderPath = videoPath.substring(0, videoPath.lastIndexOf('/'));
    try {
        const response = await fetch(`/api/files${folderPath ? '?path=' + encodeURIComponent(folderPath) : ''}`);
        const data = await response.json();

        const videoFileName = videoPath.split('/').pop();
        const videoFile = data.items.find(f => f.name === videoFileName && f.type !== 'folder');

        if (videoFile && videoFile.subtitle_languages && videoFile.subtitle_languages.length > 0) {
            videoFile.subtitle_languages.forEach(lang => {
                const option = document.createElement('option');
                option.value = lang;
                option.textContent = lang === 'default' ? 'Default' : lang.toUpperCase();
                languageSelect.appendChild(option);
            });

            // Auto-select first available subtitle
            languageSelect.value = videoFile.subtitle_languages[0];
            changeSubtitleLanguage(videoFile.subtitle_languages[0]);
        } else {
            subtitleTrack.src = '';
        }
    } catch (error) {
        console.error('Error detecting subtitle languages:', error);
        subtitleTrack.src = '';
    }
}

// Change subtitle language
async function changeSubtitleLanguage(lang) {
    if (!currentVideoPath || !lang) {
        document.getElementById('subtitleTrack').src = '';
        return;
    }

    const baseName = currentVideoPath.replace(/\.(mp4|mkv|avi|webm|mov)$/i, '');
    const srtPath = lang === 'default' ? `${baseName}.srt` : `${baseName}.${lang}.srt`;

    try {
        const response = await fetch(`/api/files/${encodeURIComponent(srtPath)}`, { method: 'HEAD' });
        if (response.ok) {
            convertSrtToVtt(srtPath).then(vttBlob => {
                const vttUrl = URL.createObjectURL(vttBlob);
                const subtitleTrack = document.getElementById('subtitleTrack');
                const video = document.getElementById('videoPlayer');
                subtitleTrack.src = vttUrl;
                video.textTracks[0].mode = 'showing';
            });
        }
    } catch (error) {
        console.error('Error loading subtitle:', error);
    }
}

// Get current subtitle text
function getCurrentSubtitleText() {
    const video = document.getElementById('videoPlayer');
    const track = video.textTracks[0];

    if (!track || track.activeCues.length === 0) {
        return null;
    }

    return track.activeCues[0].text;
}

// Translate current subtitle (hint feature)
async function translateCurrentSubtitle() {
    const currentText = getCurrentSubtitleText();

    if (!currentText) {
        showNotification('⚠️ No subtitle is currently displayed', 'error');
        return;
    }

    const currentLang = document.getElementById('subtitleLanguage').value || 'auto';
    const targetLang = 'en'; // Default to English, could make this configurable

    try {
        const response = await fetch('/api/translate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text: currentText,
                source: currentLang,
                target: targetLang
            })
        });

        const data = await response.json();

        if (response.ok) {
            document.getElementById('translationText').innerHTML = `
                <div style="margin-bottom: 8px; color: var(--text-secondary); font-size: 0.9rem;">
                    <strong>Original (${data.source_lang.toUpperCase()}):</strong> ${escapeHtml(data.original)}
                </div>
                <div style="color: var(--success-start); font-size: 1.1rem;">
                    <strong>${data.target_lang.toUpperCase()}:</strong> ${escapeHtml(data.translated)}
                </div>
            `;
            document.getElementById('translationHint').style.display = 'block';
        } else {
            showNotification(`❌ ${data.error || 'Translation failed'}`, 'error');
        }
    } catch (error) {
        console.error('Translation error:', error);
        showNotification('❌ Translation failed', 'error');
    }
}

// Close translation hint
function closeTranslationHint() {
    document.getElementById('translationHint').style.display = 'none';
}

// Helper: escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============================================================================
// CLIENT-SIDE TRANSCODING WITH FFMPEG.WASM
// ============================================================================

let ffmpegInstance = null;
let clientTranscodeAborted = false;

// Show conversion options modal (server/client/skip)
function showConversionOptionsModal(fileName, fileExt) {
    return new Promise((resolve) => {
        const modalHTML = `
            <div id="conversionOptionsModal" class="modal show" style="display: flex; align-items: center; justify-content: center;">
                <div class="modal-content" style="max-width: 600px;">
                    <h2>🎬 Convert ${fileExt} to MP4?</h2>
                    <p class="modal-subtitle">${fileName}</p>

                    <div style="margin: 30px 0; display: flex; flex-direction: column; gap: 15px;">
                        <button onclick="window.conversionChoice('server')" class="btn btn-primary" style="text-align: left; padding: 15px;">
                            <strong>🖥️ Server Conversion</strong><br>
                            <small style="opacity: 0.8;">• Fast (multi-core processing)<br>• Creates permanent MP4 file<br>• Uses server resources</small>
                        </button>

                        <button onclick="window.conversionChoice('client')" class="btn btn-secondary" style="text-align: left; padding: 15px;">
                            <strong>💻 Browser Conversion (Experimental)</strong><br>
                            <small style="opacity: 0.8;">• All processing in your browser<br>• No server load<br>• May be slower</small>
                        </button>

                        <button onclick="window.conversionChoice('skip')" class="btn btn-secondary" style="text-align: left; padding: 15px;">
                            <strong>▶️ Try Playing Anyway</strong><br>
                            <small style="opacity: 0.8;">• May not work in all browsers<br>• No conversion needed</small>
                        </button>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', modalHTML);
        const modal = document.getElementById('conversionOptionsModal');

        window.conversionChoice = (choice) => {
            modal.remove();
            delete window.conversionChoice;
            resolve(choice);
        };

        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.remove();
                delete window.conversionChoice;
                resolve('skip');
            }
        });

        const escapeHandler = (e) => {
            if (e.key === 'Escape') {
                modal.remove();
                delete window.conversionChoice;
                document.removeEventListener('keydown', escapeHandler);
                resolve('skip');
            }
        };
        document.addEventListener('keydown', escapeHandler);
    });
}

// Transcode video client-side using ffmpeg.wasm
async function transcodeClientSide(videoPath, fileName) {
    const modal = document.getElementById('clientTranscodeModal');
    const statusEl = document.getElementById('clientTranscodeStatus');
    const percentEl = document.getElementById('clientTranscodePercent');
    const progressEl = document.getElementById('clientTranscodeProgress');
    const fileNameEl = document.getElementById('clientTranscodeFileName');

    fileNameEl.textContent = `Converting: ${fileName}`;
    clientTranscodeAborted = false;

    ModalManager.open(modal);

    try {
        statusEl.textContent = 'Loading FFmpeg...';
        percentEl.textContent = '0%';
        progressEl.style.width = '0%';

        if (!ffmpegInstance) {
            const { FFmpeg } = FFmpegWASM;
            ffmpegInstance = new FFmpeg();

            ffmpegInstance.on('log', ({ message }) => {
                console.log('[FFmpeg]', message);
            });

            ffmpegInstance.on('progress', ({ progress }) => {
                if (clientTranscodeAborted) return;
                const percent = Math.round(progress * 100);
                statusEl.textContent = 'Transcoding...';
                percentEl.textContent = percent + '%';
                progressEl.style.width = percent + '%';
            });

            await ffmpegInstance.load({
                coreURL: 'https://unpkg.com/@ffmpeg/core@0.12.4/dist/umd/ffmpeg-core.js',
            });
        }

        if (clientTranscodeAborted) {
            ModalManager.close(modal);
            return null;
        }

        statusEl.textContent = 'Downloading video...';
        percentEl.textContent = '10%';
        progressEl.style.width = '10%';

        const response = await fetch(`/api/files/${encodeURIComponent(videoPath)}`);
        if (!response.ok) throw new Error('Failed to fetch video');

        const videoData = await response.arrayBuffer();

        if (clientTranscodeAborted) {
            ModalManager.close(modal);
            return null;
        }

        statusEl.textContent = 'Preparing video...';
        percentEl.textContent = '20%';
        progressEl.style.width = '20%';

        const inputName = 'input' + videoPath.substring(videoPath.lastIndexOf('.'));
        const outputName = 'output.mp4';

        await ffmpegInstance.writeFile(inputName, new Uint8Array(videoData));

        if (clientTranscodeAborted) {
            ModalManager.close(modal);
            return null;
        }

        statusEl.textContent = 'Transcoding...';

        await ffmpegInstance.exec([
            '-i', inputName,
            '-c:v', 'libx264',
            '-preset', 'ultrafast',
            '-crf', '23',
            '-c:a', 'aac',
            '-b:a', '128k',
            outputName
        ]);

        if (clientTranscodeAborted) {
            ModalManager.close(modal);
            return null;
        }

        statusEl.textContent = 'Finalizing...';
        percentEl.textContent = '95%';
        progressEl.style.width = '95%';

        const data = await ffmpegInstance.readFile(outputName);
        const blob = new Blob([data.buffer], { type: 'video/mp4' });

        await ffmpegInstance.deleteFile(inputName);
        await ffmpegInstance.deleteFile(outputName);

        statusEl.textContent = 'Complete!';
        percentEl.textContent = '100%';
        progressEl.style.width = '100%';

        setTimeout(() => ModalManager.close(modal), 500);

        return blob;

    } catch (error) {
        console.error('Client-side transcoding error:', error);
        statusEl.textContent = 'Error: ' + error.message;
        showNotification('❌ Transcoding failed: ' + error.message, 'error');

        setTimeout(() => ModalManager.close(modal), 2000);
        return null;
    }
}

// Play video from Blob object
function playVideoFromBlob(blob, fileName) {
    const modal = document.getElementById('videoModal');
    const video = document.getElementById('videoPlayer');
    const title = document.getElementById('videoTitle');

    const blobUrl = URL.createObjectURL(blob);

    currentVideoPath = blobUrl;
    title.textContent = fileName + ' (Transcoded)';

    video.src = blobUrl;

    video.onerror = function() {
        showNotification('❌ Cannot play transcoded video', 'error');
        URL.revokeObjectURL(blobUrl);
    };

    const cleanup = () => {
        URL.revokeObjectURL(blobUrl);
        video.removeEventListener('ended', cleanup);
    };
    video.addEventListener('ended', cleanup);

    ModalManager.open(modal);
    video.play();

    showNotification('✅ Playing transcoded video', 'success');
}

// Cancel client-side transcoding
function cancelClientTranscode() {
    clientTranscodeAborted = true;
    const modal = document.getElementById('clientTranscodeModal');
    ModalManager.close(modal);
    showNotification('Transcoding cancelled', 'info');
}

// ============================================================================
// System Info Functions
// ============================================================================

function loadSystemInfo() {
    fetch('/api/system-info')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                updateSystemInfo(data);
            } else {
                showNotification('Failed to load system info', 'error');
            }
        })
        .catch(error => {
            console.error('Error loading system info:', error);
            showNotification('Error loading system info', 'error');
        });
}

function updateSystemInfo(data) {
    // Update timestamp
    const timestamp = new Date(data.timestamp);
    document.getElementById('systemTimestamp').textContent =
        `Last updated: ${timestamp.toLocaleString()}`;

    // System Health
    const cpuPercent = data.system_status.cpu_percent;
    const memoryPercent = data.system_status.memory_percent;
    const diskPercent = data.system_status.disk_percent;

    document.getElementById('cpuUsage').textContent = `${cpuPercent.toFixed(1)}%`;
    document.getElementById('cpuBar').style.width = `${cpuPercent}%`;
    document.getElementById('cpuBar').style.background = getProgressColor(cpuPercent);

    document.getElementById('memoryUsage').textContent =
        `${data.system_status.memory_used_gb.toFixed(1)} GB / ${data.system_status.memory_total_gb.toFixed(1)} GB (${memoryPercent.toFixed(1)}%)`;
    document.getElementById('memoryBar').style.width = `${memoryPercent}%`;
    document.getElementById('memoryBar').style.background = getProgressColor(memoryPercent);

    document.getElementById('diskUsage').textContent =
        `${data.system_status.disk_used_gb.toFixed(1)} GB / ${data.system_status.disk_total_gb.toFixed(1)} GB (${diskPercent.toFixed(1)}%)`;
    document.getElementById('diskBar').style.width = `${diskPercent}%`;
    document.getElementById('diskBar').style.background = getProgressColor(diskPercent);

    // Database Health
    document.getElementById('dbStatus').textContent =
        data.database.accessible ? '✅ Accessible' : '❌ Not Accessible';
    document.getElementById('dbSize').textContent =
        `${data.database.size_mb} MB`;
    document.getElementById('dbJobCount').textContent =
        data.database.job_count || 'N/A';

    // Directory Sizes
    const dirs = data.directories;
    document.getElementById('dirDownloads').textContent =
        dirs.yt_downloads.exists ? `${dirs.yt_downloads.size_gb} GB (${dirs.yt_downloads.file_count} files)` : 'N/A';
    document.getElementById('dirUploads').textContent =
        dirs.uploads.exists ? `${dirs.uploads.size_gb} GB (${dirs.uploads.file_count} files)` : 'N/A';
    document.getElementById('dirLogs').textContent =
        dirs.logs.exists ? `${dirs.logs.size_mb} MB (${dirs.logs.file_count} files)` : 'N/A';
    document.getElementById('dirBackups').textContent =
        dirs.backups.exists ? `${dirs.backups.size_gb} GB (${dirs.backups.file_count} files)` : 'N/A';

    // Process Information
    const process = data.process;
    document.getElementById('processPid').textContent = process.pid;
    document.getElementById('processStatus').textContent = process.status;
    document.getElementById('processMemory').textContent = `${process.memory_mb} MB (${process.memory_percent}%)`;
    document.getElementById('processThreads').textContent = process.threads;

    const createTime = new Date(process.create_time);
    const now = new Date();
    const uptime = Math.floor((now - createTime) / 1000);
    document.getElementById('processUptime').textContent = formatUptime(uptime);

    // GPU Information
    const gpuContainer = document.getElementById('gpuInfo');
    if (data.gpu.available) {
        let gpuHTML = '<div class="info-grid">';
        gpuHTML += `<div class="info-item"><span class="info-label">Status:</span><span>✅ Available</span></div>`;
        gpuHTML += `<div class="info-item"><span class="info-label">GPU Count:</span><span>${data.gpu.count}</span></div>`;
        gpuHTML += `<div class="info-item"><span class="info-label">CUDA Version:</span><span>${data.gpu.cuda_version || 'N/A'}</span></div>`;
        gpuHTML += `<div class="info-item"><span class="info-label">cuDNN Version:</span><span>${data.gpu.cudnn_version || 'N/A'}</span></div>`;
        gpuHTML += '</div>';

        // Device details
        data.gpu.devices.forEach((device, idx) => {
            gpuHTML += `<div style="margin-top: 15px; padding: 15px; background: rgba(102, 126, 234, 0.05); border-radius: 8px;">`;
            gpuHTML += `<h4 style="margin: 0 0 10px 0;">GPU ${device.id}: ${device.name}</h4>`;
            gpuHTML += '<div class="info-grid">';
            gpuHTML += `<div class="info-item"><span class="info-label">Memory:</span><span>${device.total_memory_gb} GB</span></div>`;
            gpuHTML += `<div class="info-item"><span class="info-label">Compute Capability:</span><span>${device.capability}</span></div>`;
            gpuHTML += `<div class="info-item"><span class="info-label">Multiprocessors:</span><span>${device.multi_processor_count}</span></div>`;
            gpuHTML += '</div></div>';
        });

        gpuContainer.innerHTML = gpuHTML;
    } else {
        gpuContainer.innerHTML = `<p style="color: var(--text-secondary);">❌ ${data.gpu.message || data.gpu.error || 'GPU not available'}</p>`;
    }

    // System Information
    const sys = data.system;
    document.getElementById('sysPlatform').textContent = `${sys.platform} ${sys.platform_release}`;
    document.getElementById('sysArch').textContent = sys.architecture;
    document.getElementById('sysProcessor').textContent = sys.processor || 'N/A';
    document.getElementById('sysPython').textContent = sys.python_version;
    document.getElementById('sysCpuPhysical').textContent = sys.cpu_count_physical;
    document.getElementById('sysCpuLogical').textContent = sys.cpu_count_logical;
}

function getProgressColor(percent) {
    if (percent < 60) {
        return 'linear-gradient(90deg, #10b981, #34d399)'; // Green
    } else if (percent < 80) {
        return 'linear-gradient(90deg, #f59e0b, #fbbf24)'; // Yellow
    } else {
        return 'linear-gradient(90deg, #ef4444, #f87171)'; // Red
    }
}

function formatUptime(seconds) {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;

    const parts = [];
    if (days > 0) parts.push(`${days}d`);
    if (hours > 0) parts.push(`${hours}h`);
    if (minutes > 0) parts.push(`${minutes}m`);
    if (secs > 0 || parts.length === 0) parts.push(`${secs}s`);

    return parts.join(' ');
}
