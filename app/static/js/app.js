/**
 * Asisten Tutor UT MKWN4108 — Bahasa Indonesia
 * Dashboard Controller (Alpine.js)
 * Tema: Warm Honey & Sunlight Gold
 */

document.addEventListener('alpine:init', () => {
  Alpine.data('tutonDashboard', () => ({
    // Data State
    courses: [],
    sessions: [],
    recap: {
      total_students: 0,
      completed_students: 0,
      pending_students: 0,
      completion_rate: 0,
      matrix: {}
    },
    students: [],
    loading: true,
    studentsLoading: false,

    // Filter Toolbar State
    selectedCourse: '',
    selectedSession: null,
    statusFilter: 'pending', // Default tampilkan yang belum dinilai ('pending')
    searchQuery: '',

    // Micro-interaction Feedback Maps (nim_session -> boolean)
    copiedFeedbacks: {},
    copiedGrades: {},

    // Scan Modal State
    scanModalOpen: false,
    scanForm: {
      session_num: null,
      course_id: '',
      dry_run: false
    },
    scanStatus: {
      is_running: false,
      progress: 0,
      message: 'Siap memindai',
      current_step: '',
      log: []
    },
    scanPollingTimer: null,

    // Edit Submission Modal State
    editModalOpen: false,
    editForm: {
      student_nim: '',
      student_name: '',
      course_id: '',
      session_num: 1,
      score: 85,
      feedback: ''
    },

    // Notification Toast
    toast: {
      show: false,
      message: '',
      type: 'success',
      timer: null
    },

    // Course Code Mapping Fallback
    courseMap: {
      '413073': { code: 'MKWN4108.2137', name: 'Bahasa Indonesia 2137' },
      '413077': { code: 'MKWN4108.2141', name: 'Bahasa Indonesia 2141' },
      '413081': { code: 'MKWN4108.2145', name: 'Bahasa Indonesia 2145' },
      '411401': { code: 'MKWN4108.465', name: 'Bahasa Indonesia 465' }
    },

    /**
     * Inisialisasi Dashboard
     */
    async init() {
      try {
        await Promise.all([
          this.fetchCourses(),
          this.fetchSessions(),
          this.fetchRecap()
        ]);
        await this.fetchStudents();
        await this.checkInitialScanStatus();
      } catch (err) {
        console.error('Inisialisasi dashboard gagal:', err);
        this.showToast('Gagal memuat beberapa data sistem', 'error');
      } finally {
        this.loading = false;
        this.refreshIcons();
      }
    },

    /**
     * Muat daftar kelas
     */
    async fetchCourses() {
      try {
        const res = await fetch('/api/courses');
        if (res.ok) {
          const data = await res.json();
          if (Array.isArray(data) && data.length > 0) {
            this.courses = data;
            data.forEach(c => {
              this.courseMap[String(c.id)] = { code: c.code, name: c.name };
            });
            return;
          }
        }
      } catch (e) {
        console.warn('Menggunakan fallback daftar kelas:', e);
      }
      // Default fallback
      this.courses = [
        { id: '413073', code: 'MKWN4108.2137', name: 'Bahasa Indonesia 2137' },
        { id: '413077', code: 'MKWN4108.2141', name: 'Bahasa Indonesia 2141' },
        { id: '413081', code: 'MKWN4108.2145', name: 'Bahasa Indonesia 2145' },
        { id: '411401', code: 'MKWN4108.465', name: 'Bahasa Indonesia 465' }
      ];
    },

    /**
     * Muat daftar 8 sesi perkuliahan
     */
    async fetchSessions() {
      try {
        const res = await fetch('/api/sessions');
        if (res.ok) {
          this.sessions = await res.json();
          return;
        }
      } catch (e) {
        console.warn('Gagal memuat sesi:', e);
      }
      // Default fallback 8 sesi
      this.sessions = Array.from({ length: 8 }, (_, i) => {
        const s = i + 1;
        const isTugas = [3, 5, 7].includes(s);
        return {
          session_num: s,
          type: isTugas ? 'tugas' : 'diskusi',
          title: isTugas ? `Sesi ${s}: Tugas ${(s + 1) / 2 - 1}` : `Sesi ${s}: Diskusi`,
          status: s <= 2 ? 'active' : 'upcoming'
        };
      });
    },

    /**
     * Muat rekapitulasi progres (matriks 4x8 & metrik global)
     */
    async fetchRecap() {
      try {
        const res = await fetch('/api/recap');
        if (res.ok) {
          this.recap = await res.json();
        }
      } catch (e) {
        console.error('Gagal memuat rekap:', e);
      }
    },

    /**
     * Muat data mahasiswa dengan trajektori & rekomendasi skor
     */
    async fetchStudents() {
      this.studentsLoading = true;
      try {
        const params = new URLSearchParams();
        if (this.selectedCourse) {
          params.append('course_id', this.selectedCourse);
        }
        if (this.selectedSession !== null && this.selectedSession !== '') {
          params.append('session_num', this.selectedSession);
        }
        const url = `/api/students?${params.toString()}`;
        const res = await fetch(url);
        if (res.ok) {
          this.students = await res.json();
        }
      } catch (e) {
        console.error('Gagal memuat mahasiswa:', e);
        this.showToast('Gagal memuat daftar mahasiswa', 'error');
      } finally {
        this.studentsLoading = false;
        this.refreshIcons();
      }
    },

    /**
     * Saring berdasarkan klik sel matriks (Course x Session)
     */
    filterByCell(courseId, sessionNum) {
      this.selectedCourse = String(courseId);
      this.selectedSession = Number(sessionNum);
      const cell = this.getMatrixCell(courseId, sessionNum);
      this.statusFilter = (cell && cell.pending > 0) ? 'pending' : 'all';
      this.searchQuery = '';
      this.fetchStudents();

      const courseCode = this.getCourseCode(courseId);
      const modeLabel = (cell && cell.pending > 0) ? `(${cell.pending} Perlu Tindakan)` : '(Semua Mahasiswa)';
      this.showToast(`Menyaring: ${courseCode} • Sesi ${sessionNum} ${modeLabel}`, 'info');

      // Scroll mulus ke daftar mahasiswa
      const el = document.getElementById('student-list-section');
      if (el) {
        el.scrollIntoView({ behavior: 'smooth' });
      }
    },

    /**
     * Reset semua filter
     */
    resetFilters() {
      this.selectedCourse = '';
      this.selectedSession = null;
      this.statusFilter = 'pending';
      this.searchQuery = '';
      this.fetchStudents();
      this.showToast('Filter direset (menampilkan mahasiswa yang perlu tindakan)', 'info');
    },

    /**
     * Mendapatkan daftar mahasiswa yang telah disaring secara reaktif di klien
     */
    get filteredStudents() {
      let list = this.students;

      // Filter Status
      if (this.statusFilter === 'pending') {
        list = list.filter(s => s.status === 'pending' || s.current_score === null || s.current_score === undefined);
      } else if (this.statusFilter === 'evaluated') {
        list = list.filter(s => ['completed', 'evaluated', 'copied', 'graded'].includes(s.status) || (s.current_score !== null && s.current_score !== undefined && s.status !== 'pending'));
      }

      // Filter Pencarian Teks (Nama atau NIM)
      if (this.searchQuery && this.searchQuery.trim() !== '') {
        const q = this.searchQuery.trim().toLowerCase();
        list = list.filter(s => {
          const name = (s.name || '').toLowerCase();
          const nim = (s.nim || '').toLowerCase();
          return name.includes(q) || nim.includes(q);
        });
      }

      return list;
    },

    /**
     * Helper counts untuk pills filter status
     */
    get countAll() {
      return this.students.length;
    },
    get countPending() {
      return this.students.filter(s => s.status === 'pending' || s.current_score === null || s.current_score === undefined).length;
    },
    get countEvaluated() {
      return this.students.filter(s => ['completed', 'evaluated', 'copied', 'graded'].includes(s.status) || (s.current_score !== null && s.current_score !== undefined && s.status !== 'pending')).length;
    },

    /**
     * Informasi sesi yang sedang berjalan
     */
    get activeSessionInfo() {
      const active = this.sessions.filter(s => s.status === 'active');
      if (active.length > 0) {
        return active.map(s => `Sesi ${s.session_num}`).join(' & ') + ' Aktif';
      }
      return 'Sesi 4 & 5 Aktif';
    },

    /**
     * 1-Click Salin Feedback
     */
    async copyFeedback(student) {
      if (!student || !student.feedback) {
        this.showToast('Draf feedback belum tersedia untuk disalin', 'warning');
        return;
      }

      const text = student.feedback;
      const key = `${student.nim}_${student.current_session || 1}`;

      try {
        await this.writeToClipboard(text);
        
        // Aktifkan micro-interaction
        this.copiedFeedbacks[key] = true;
        student.is_copied = 1;

        // Reset micro-interaction setelah 2.5 detik
        setTimeout(() => {
          this.copiedFeedbacks[key] = false;
        }, 2500);

        // Kirim penandaan ke backend
        fetch('/api/submissions/copy-feedback', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            student_nim: student.nim,
            course_id: student.course_id,
            session_num: student.current_session || 1
          })
        }).catch(err => console.error('Gagal mencatat copy-feedback:', err));

        this.showToast(`Feedback ${student.name} berhasil disalin! ✓`, 'success');
      } catch (err) {
        console.error('Clipboard copy failed:', err);
        this.showToast('Gagal menyalin teks ke papan klip', 'error');
      }
    },

    /**
     * 1-Click Salin Nilai
     */
    async copyGrade(student) {
      const scoreToCopy = student.current_score !== null && student.current_score !== undefined
        ? student.current_score
        : (student.suggested_score !== null && student.suggested_score !== undefined ? student.suggested_score : 85);

      const key = `${student.nim}_${student.current_session || 1}`;

      try {
        await this.writeToClipboard(String(scoreToCopy));

        // Aktifkan micro-interaction
        this.copiedGrades[key] = true;
        student.is_grade_copied = 1;

        setTimeout(() => {
          this.copiedGrades[key] = false;
        }, 2500);

        // Catat ke backend
        fetch('/api/submissions/copy-grade', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            student_nim: student.nim,
            course_id: student.course_id,
            session_num: student.current_session || 1
          })
        }).catch(err => console.error('Gagal mencatat copy-grade:', err));

        this.showToast(`Nilai (${scoreToCopy}) berhasil disalin! ✓`, 'success');
      } catch (err) {
        console.error('Clipboard copy failed:', err);
        this.showToast('Gagal menyalin nilai angka', 'error');
      }
    },

    /**
     * Helper universal clipboard write dengan fallback
     */
    async writeToClipboard(text) {
      if (navigator.clipboard && window.isSecureContext) {
        return navigator.clipboard.writeText(text);
      } else {
        // Fallback untuk context tanpa HTTPS / iframe
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        textArea.style.top = '-999999px';
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        return new Promise((resolve, reject) => {
          document.execCommand('copy') ? resolve() : reject(new Error('ExecCommand copy failed'));
          textArea.remove();
        });
      }
    },

    /**
     * Buka modal edit penilaian/feedback
     */
    openEditModal(student) {
      this.editForm = {
        student_nim: student.nim,
        student_name: student.name,
        course_id: student.course_id,
        session_num: student.current_session || 1,
        score: student.current_score !== null ? student.current_score : (student.suggested_score || 85),
        original_score: student.current_score,
        feedback: student.feedback || ''
      };
      this.editModalOpen = true;
    },

    /**
     * Simpan perubahan nilai / feedback
     */
    async saveSubmission() {
      try {
        const payload = {
          student_nim: this.editForm.student_nim,
          course_id: this.editForm.course_id,
          session_num: Number(this.editForm.session_num),
          score: Number(this.editForm.score),
          original_score: this.editForm.original_score,
          feedback: this.editForm.feedback,
          status: 'evaluated'
        };

        const res = await fetch('/api/submissions/update', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        if (res.ok) {
          this.editModalOpen = false;
          this.showToast('Perubahan penilaian berhasil disimpan!', 'success');
          await Promise.all([this.fetchRecap(), this.fetchStudents()]);
        } else {
          this.showToast('Gagal menyimpan perubahan penilaian', 'error');
        }
      } catch (err) {
        console.error('Error saving submission:', err);
        this.showToast('Terjadi kesalahan saat menyimpan', 'error');
      }
    },

    /**
     * Buka Scan Modal
     */
    openScanModal(sessionNum = null, courseId = '') {
      this.scanForm.session_num = sessionNum !== null ? sessionNum : (this.selectedSession || '');
      this.scanForm.course_id = courseId || this.selectedCourse || '';
      this.scanForm.dry_run = false;
      this.scanModalOpen = true;
      this.refreshIcons();
    },

    /**
     * Cek status pemindaian saat inisialisasi
     */
    async checkInitialScanStatus() {
      try {
        const res = await fetch('/api/scan/status');
        if (res.ok) {
          const data = await res.json();
          this.scanStatus = data;
          if (data.is_running) {
            this.scanModalOpen = true;
            this.startScanPolling();
          }
        }
      } catch (e) {
        console.warn('Gagal cek status scan:', e);
      }
    },

    /**
     * Jalankan Scan dari modal
     */
    async triggerScan() {
      try {
        const payload = {
          session_num: this.scanForm.session_num ? Number(this.scanForm.session_num) : null,
          course_id: this.scanForm.course_id ? String(this.scanForm.course_id) : null,
          dry_run: Boolean(this.scanForm.dry_run)
        };

        const res = await fetch('/api/scan', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        if (res.ok) {
          const data = await res.json();
          this.showToast('Pemindaian dimulai...', 'info');
          this.startScanPolling();
        } else {
          this.showToast('Gagal memulai proses pemindaian', 'error');
        }
      } catch (err) {
        console.error('Error starting scan:', err);
        this.showToast('Kesalahan koneksi saat memulai scan', 'error');
      }
    },

    /**
     * Polling status pemindaian secara berkala (1s)
     */
    startScanPolling() {
      if (this.scanPollingTimer) clearInterval(this.scanPollingTimer);
      
      this.scanPollingTimer = setInterval(async () => {
        try {
          const res = await fetch('/api/scan/status');
          if (res.ok) {
            const data = await res.json();
            this.scanStatus = data;
            
            if (!data.is_running) {
              clearInterval(this.scanPollingTimer);
              this.scanPollingTimer = null;
              this.showToast('Pemindaian selesai! Memperbarui data...', 'success');
              await Promise.all([this.fetchRecap(), this.fetchStudents()]);
            }
          }
        } catch (err) {
          console.error('Polling error:', err);
        }
      }, 1000);
    },

    /**
     * Batalkan polling saat modal ditutup
     */
    closeScanModal() {
      if (!this.scanStatus.is_running) {
        this.scanModalOpen = false;
      } else {
        // Biarkan tetap berjalan di background
        this.scanModalOpen = false;
        this.showToast('Pemindaian tetap berjalan di latar belakang', 'info');
      }
    },

    /**
     * Ekspor CSV
     */
    exportCsv() {
      window.location.href = '/api/export';
      this.showToast('Mengunduh rekapitulasi penilaian CSV...', 'info');
    },

    /**
     * Helper Kode Kelas
     */
    getCourseCode(courseId) {
      const c = this.courseMap[String(courseId)];
      return c ? c.code : `Kelas ${courseId}`;
    },

    /**
     * Helper Format Badge Tipe Sesi (Diskusi vs Tugas)
     */
    isSessionTugas(sessionNum) {
      return [3, 5, 7].includes(Number(sessionNum));
    },

    /**
     * Helper Sel Matriks
     */
    getMatrixCell(courseId, sessionNum) {
      if (this.recap && this.recap.matrix && this.recap.matrix[String(courseId)]) {
        const cell = this.recap.matrix[String(courseId)][Number(sessionNum)];
        if (cell) return cell;
      }
      return { completed: 0, pending: 0, total: 0, rate: 0 };
    },

    /**
     * Tampilkan Toast Notifikasi
     */
    showToast(message, type = 'success') {
      if (this.toast.timer) clearTimeout(this.toast.timer);
      this.toast.message = message;
      this.toast.type = type;
      this.toast.show = true;

      this.toast.timer = setTimeout(() => {
        this.toast.show = false;
      }, 3000);
    },

    /**
     * Refresh Lucide Icons DOM
     */
    refreshIcons() {
      this.$nextTick(() => {
        if (window.lucide && typeof window.lucide.createIcons === 'function') {
          window.lucide.createIcons();
        }
      });
    }
  }));
});
