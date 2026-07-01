import React from "react";

export const VoiceAssistantCard = ({
  canUseVoiceChat,
  voiceStatus,
  voiceAccessLoading,
  isListening,
  voiceBusy,
  startVoiceCapture,
  stopVoiceCapture,
  MicIcon,
  voiceTranscript = "",
  voiceAnswer = "",
}) => (
  <div className="voice-assistant-panel">
    <div className="voice-assistant-top">
      <span className="voice-assistant-label">Voice Assistant</span>
      <div className="voice-assistant-actions">
        <button
          type="button"
          className={`voice-action-btn ${isListening || voiceBusy ? "active" : ""}`}
          onClick={isListening || voiceBusy ? stopVoiceCapture : startVoiceCapture}
          disabled={voiceAccessLoading || !canUseVoiceChat || voiceBusy}
          aria-label={isListening || voiceBusy ? "Stop voice assistant" : "Start voice assistant"}
        >
          <MicIcon />
          <span>{voiceAccessLoading ? "Checking..." : (isListening || voiceBusy ? "Stop" : "Start")}</span>
        </button>
      </div>
      <span className="voice-assistant-status-inline">{voiceStatus}</span>
    </div>
    {voiceTranscript ? (
      <div className="voice-transcript">
        <strong>You said:</strong> {voiceTranscript}
      </div>
    ) : null}
    {voiceAnswer ? (
      <div className="voice-answer">
        <strong>Assistant:</strong> {voiceAnswer}
      </div>
    ) : null}
  </div>
);

export const ClassSelectionPage = ({
  currentUser,
  teacherEnabled,
  adminEnabled,
  handleSignOut,
  handleSignIn,
  UserIcon,
  authStatus,
  studentStatus,
  studentLoading,
  studentClasses,
  loadStudentClasses,
  enrollAndOpenClass,
  canUseVoiceChat,
  voiceStatus,
  voiceAccessLoading,
  isListening,
  voiceBusy,
  voiceTranscript,
  voiceAnswer,
  startVoiceCapture,
  stopVoiceCapture,
  MicIcon,
}) => (
  <div className="container" style={{ padding: "18px", overflow: "auto" }}>
    <header style={{ padding: 0, borderBottom: "none", marginBottom: "12px" }}>
      <h1>📚 Course Home</h1>
      <div className="controls">
        {currentUser && teacherEnabled && (
          <button type="button" className="account-action-btn" onClick={() => { window.location.href = "/teacher-courses"; }}>
            Teacher
          </button>
        )}
        {currentUser && adminEnabled && (
          <button type="button" className="account-action-btn" onClick={() => { window.location.href = "/admin"; }}>
            Admin
          </button>
        )}
        <button type="button" className="account-action-btn" onClick={currentUser ? handleSignOut : handleSignIn}>
          <UserIcon />
          <span>{currentUser ? "Sign out" : "Sign in"}</span>
        </button>
      </div>
    </header>
    <div className="identity-status" style={{ margin: "0 0 12px" }}>{authStatus}</div>
    <VoiceAssistantCard
      canUseVoiceChat={canUseVoiceChat}
      voiceStatus={voiceStatus}
      voiceAccessLoading={voiceAccessLoading}
      isListening={isListening}
      voiceBusy={voiceBusy}
      voiceTranscript={voiceTranscript}
      voiceAnswer={voiceAnswer}
      startVoiceCapture={startVoiceCapture}
      stopVoiceCapture={stopVoiceCapture}
      MicIcon={MicIcon}
    />
    {!currentUser && <div style={{ color: "#4b5563" }}>Sign in to view your course.</div>}
    {currentUser && (
      <div style={{ border: "1px solid #e5e7eb", borderRadius: "8px", padding: "12px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
          <strong>Available courses</strong>
          <button
            type="button"
            onClick={() => loadStudentClasses()}
            disabled={studentLoading}
            style={{ borderRadius: "14px", border: "1px solid #ddd", padding: "4px 10px", background: "#fff" }}
          >
            Refresh
          </button>
        </div>
        {studentStatus && <div style={{ fontSize: "0.9rem", color: "#4b5563", marginBottom: "8px" }}>{studentStatus}</div>}
        {studentLoading && <div style={{ color: "#6b7280" }}>Loading your courses...</div>}
        {!studentLoading && studentClasses.length === 0 && <div style={{ color: "#6b7280" }}>No course available</div>}
        {!studentLoading && studentClasses.length > 0 && (
          <div style={{ maxHeight: "420px", overflow: "auto", border: "1px solid #f3f4f6", borderRadius: "6px" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.9rem" }}>
              <thead>
                <tr style={{ background: "#fafafa" }}>
                  <th style={{ textAlign: "left", padding: "8px" }}>Course</th>
                  <th style={{ textAlign: "left", padding: "8px" }}>Teacher</th>
                  <th style={{ textAlign: "left", padding: "8px" }}>Status</th>
                  <th style={{ textAlign: "right", padding: "8px" }}>Open</th>
                </tr>
              </thead>
              <tbody>
                {studentClasses.map((item) => (
                  <tr key={item.class_id}>
                    <td style={{ padding: "8px", borderTop: "1px solid #f3f4f6" }}>
                      <div>{item.course_title || item.course_id || "-"}</div>
                      <div style={{ color: "#6b7280", fontSize: "0.8rem" }}>Class ID: {item.class_id}</div>
                    </td>
                    <td style={{ padding: "8px", borderTop: "1px solid #f3f4f6" }}>{item.teacher_email || item.teacher_uid || "-"}</td>
                    <td style={{ padding: "8px", borderTop: "1px solid #f3f4f6" }}>
                      {item.is_public ? "public" : (item.enrolled ? "enrolled" : "not enrolled")}
                    </td>
                    <td style={{ padding: "8px", borderTop: "1px solid #f3f4f6", textAlign: "right" }}>
                      <button
                        type="button"
                        onClick={() => enrollAndOpenClass(item.class_id)}
                        disabled={studentLoading}
                        style={{ borderRadius: "12px", border: "1px solid #ddd", padding: "4px 10px", background: "#fff" }}
                      >
                        Open course
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    )}
  </div>
);

export const TeacherWorkspacePage = ({
  currentUser,
  teacherEnabled,
  teacherLoading,
  teacherStatus,
  teacherCourses,
  teacherClasses,
  teacherCourseTitle,
  setTeacherCourseTitle,
  teacherCourseLanguages,
  setTeacherCourseLanguages,
  teacherCloneCourseId,
  setTeacherCloneCourseId,
  teacherCloneClassTitle,
  setTeacherCloneClassTitle,
  teacherClassIsPublic,
  setTeacherClassIsPublic,
  teacherPackageBucket,
  setTeacherPackageBucket,
  teacherPackagePrefix,
  setTeacherPackagePrefix,
  teacherPackageManifestUrl,
  setTeacherPackageManifestUrl,
  teacherUploadFilePaths,
  setTeacherUploadFilePaths,
  teacherUploadUrls,
  createTeacherCourse,
  cloneTeacherClass,
  linkTeacherCoursePackage,
  createClassFromPackage,
  createTeacherUploadSession,
  updateTeacherCourseTitle,
  loadTeacherWorkspace,
  handleSignOut,
  handleSignIn,
  UserIcon,
  authStatus,
}) => (
  <div className="container" style={{ padding: "18px", overflow: "auto" }}>
    <header style={{ padding: 0, borderBottom: "none", marginBottom: "12px" }}>
      <h1>🧑‍🏫 Teacher Courses & Classes</h1>
      <div className="controls">
        <button type="button" className="account-action-btn" onClick={() => { window.location.href = "/"; }}>
          Back to Class Selection
        </button>
        <button type="button" className="account-action-btn" onClick={currentUser ? handleSignOut : handleSignIn}>
          <UserIcon />
          <span>{currentUser ? "Sign out" : "Sign in"}</span>
        </button>
      </div>
    </header>
    <div className="identity-status" style={{ margin: "0 0 12px" }}>{authStatus}</div>
    {!currentUser && <div style={{ color: "#4b5563" }}>Sign in with a teacher account to manage courses and classes.</div>}
    {currentUser && !teacherEnabled && <div style={{ color: "#b91c1c" }}>This account does not have teacher access.</div>}
    {currentUser && teacherEnabled && (
      <div style={{ border: "1px solid #e5e7eb", borderRadius: "8px", padding: "12px" }}>
        <div style={{ display: "flex", gap: "8px", alignItems: "center", flexWrap: "wrap", marginBottom: "10px" }}>
          <label style={{ fontSize: "0.9rem" }}>
            Course title
            <input
              type="text"
              value={teacherCourseTitle}
              onChange={(e) => setTeacherCourseTitle(e.target.value)}
              placeholder="Cloud Fundamentals"
              style={{ marginLeft: "6px", width: "220px" }}
            />
          </label>
          <label style={{ fontSize: "0.9rem" }}>
            Languages
            <input
              type="text"
              value={teacherCourseLanguages}
              onChange={(e) => setTeacherCourseLanguages(e.target.value)}
              placeholder="en-US,zh-CN,yue-HK"
              style={{ marginLeft: "6px", width: "200px" }}
            />
          </label>
          <button type="button" onClick={createTeacherCourse} disabled={teacherLoading}>Create course</button>
        </div>
        <div style={{ display: "flex", gap: "8px", alignItems: "center", flexWrap: "wrap", marginBottom: "10px" }}>
          <label style={{ fontSize: "0.9rem" }}>
            Select course
            <select
              value={teacherCloneCourseId}
              onChange={(e) => setTeacherCloneCourseId(e.target.value)}
              style={{ marginLeft: "6px", width: "220px" }}
            >
              <option value="">Select course</option>
              {teacherCourses.map((course) => (
                <option key={course.course_id} value={course.course_id}>
                  {course.title || course.course_id}
                </option>
              ))}
            </select>
          </label>
          <label style={{ fontSize: "0.9rem" }}>
            Class title
            <input
              type="text"
              value={teacherCloneClassTitle}
              onChange={(e) => setTeacherCloneClassTitle(e.target.value)}
              placeholder="2026A Cohort"
              style={{ marginLeft: "6px", width: "180px" }}
            />
          </label>
          <label style={{ fontSize: "0.9rem", display: "inline-flex", alignItems: "center", gap: "6px" }}>
            <input
              type="checkbox"
              checked={teacherClassIsPublic}
              onChange={(e) => setTeacherClassIsPublic(e.target.checked)}
            />
            Public class
          </label>
          <button type="button" onClick={createClassFromPackage} disabled={teacherLoading}>Create class from package</button>
          <button type="button" onClick={cloneTeacherClass} disabled={teacherLoading}>Legacy clone</button>
          <button type="button" onClick={() => loadTeacherWorkspace()} disabled={teacherLoading}>Refresh</button>
        </div>
        <div style={{ borderTop: "1px solid #f3f4f6", paddingTop: "8px", marginBottom: "10px" }}>
          <div style={{ fontWeight: 600, marginBottom: "6px" }}>Course package</div>
          <div style={{ display: "flex", gap: "8px", alignItems: "center", flexWrap: "wrap", marginBottom: "8px" }}>
            <label style={{ fontSize: "0.9rem" }}>
              Bucket
              <input
                type="text"
                value={teacherPackageBucket}
                onChange={(e) => setTeacherPackageBucket(e.target.value)}
                placeholder="course-package-bucket"
                style={{ marginLeft: "6px", width: "220px" }}
              />
            </label>
            <label style={{ fontSize: "0.9rem" }}>
              Prefix
              <input
                type="text"
                value={teacherPackagePrefix}
                onChange={(e) => setTeacherPackagePrefix(e.target.value)}
                placeholder="course-packages/course_id/v20260701"
                style={{ marginLeft: "6px", width: "260px" }}
              />
            </label>
            <label style={{ fontSize: "0.9rem" }}>
              Manifest URL
              <input
                type="text"
                value={teacherPackageManifestUrl}
                onChange={(e) => setTeacherPackageManifestUrl(e.target.value)}
                placeholder="https://cdn.example.com/course/manifest.json"
                style={{ marginLeft: "6px", width: "320px" }}
              />
            </label>
            <button type="button" onClick={linkTeacherCoursePackage} disabled={teacherLoading}>Link & validate package</button>
          </div>
          <div style={{ display: "flex", gap: "8px", alignItems: "flex-start", flexWrap: "wrap" }}>
            <label style={{ fontSize: "0.9rem" }}>
              Upload file paths (one per line)
              <textarea
                value={teacherUploadFilePaths}
                onChange={(e) => setTeacherUploadFilePaths(e.target.value)}
                placeholder={"manifest.json\nassets/en/slide_1.png\naudio/en/slide_1.audio"}
                rows={4}
                style={{ marginLeft: "6px", width: "300px", resize: "vertical" }}
              />
            </label>
            <button type="button" onClick={createTeacherUploadSession} disabled={teacherLoading}>Create upload session</button>
          </div>
          {Array.isArray(teacherUploadUrls) && teacherUploadUrls.length > 0 && (
            <div style={{ marginTop: "8px", maxHeight: "140px", overflow: "auto", border: "1px solid #f3f4f6", borderRadius: "6px", padding: "6px", fontSize: "0.8rem" }}>
              {teacherUploadUrls.map((item) => (
                <div key={item.object_name} style={{ marginBottom: "4px" }}>
                  <strong>{item.path}</strong>
                  <div style={{ wordBreak: "break-all" }}>{item.upload_url}</div>
                </div>
              ))}
            </div>
          )}
        </div>
        {teacherStatus && <div style={{ color: "#4b5563", marginBottom: "10px" }}>{teacherStatus}</div>}
        <div style={{ fontWeight: 600, marginBottom: "6px" }}>Courses</div>
        <div style={{ maxHeight: "220px", overflow: "auto", border: "1px solid #f3f4f6", borderRadius: "6px", marginBottom: "10px" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
            <thead>
              <tr style={{ background: "#fafafa" }}>
                <th style={{ textAlign: "left", padding: "6px" }}>Course</th>
                <th style={{ textAlign: "left", padding: "6px" }}>Languages</th>
                <th style={{ textAlign: "left", padding: "6px" }}>Package</th>
                <th style={{ textAlign: "right", padding: "6px" }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {teacherCourses.map((course) => (
                <tr key={course.course_id}>
                  <td style={{ padding: "6px", borderTop: "1px solid #f3f4f6" }}>{course.title || course.course_id}</td>
                  <td style={{ padding: "6px", borderTop: "1px solid #f3f4f6" }}>{(course.languages || []).join(", ")}</td>
                  <td style={{ padding: "6px", borderTop: "1px solid #f3f4f6" }}>
                    {course.package_manifest_url || "-"}
                  </td>
                  <td style={{ padding: "6px", borderTop: "1px solid #f3f4f6", textAlign: "right" }}>
                    <button type="button" onClick={() => updateTeacherCourseTitle(course)} disabled={teacherLoading}>Rename</button>
                  </td>
                </tr>
              ))}
            {teacherCourses.length === 0 && (
              <tr><td colSpan={4} style={{ padding: "8px", color: "#6b7280" }}>No courses</td></tr>
            )}
            </tbody>
          </table>
        </div>
        <div style={{ fontWeight: 600, marginBottom: "6px" }}>Classes</div>
        <div style={{ maxHeight: "220px", overflow: "auto", border: "1px solid #f3f4f6", borderRadius: "6px" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
            <thead>
              <tr style={{ background: "#fafafa" }}>
                <th style={{ textAlign: "left", padding: "6px" }}>Class</th>
                <th style={{ textAlign: "left", padding: "6px" }}>Course</th>
                <th style={{ textAlign: "left", padding: "6px" }}>Current presentation</th>
              </tr>
            </thead>
            <tbody>
              {teacherClasses.map((classItem) => (
                <tr key={classItem.class_id}>
                  <td style={{ padding: "6px", borderTop: "1px solid #f3f4f6" }}>{classItem.title || classItem.class_id}</td>
                  <td style={{ padding: "6px", borderTop: "1px solid #f3f4f6" }}>{classItem.course_id}</td>
                  <td style={{ padding: "6px", borderTop: "1px solid #f3f4f6" }}>{classItem.current_presentation_id || "-"}</td>
                </tr>
              ))}
              {teacherClasses.length === 0 && (
                <tr><td colSpan={3} style={{ padding: "8px", color: "#6b7280" }}>No classes</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    )}
  </div>
);

export const AdminIndexPage = ({
  currentUser,
  adminEnabled,
  handleSignOut,
  handleSignIn,
  UserIcon,
  authStatus,
}) => (
  <div className="container" style={{ padding: "18px", overflow: "auto" }}>
    <header style={{ padding: 0, borderBottom: "none", marginBottom: "12px" }}>
      <h1>🛠️ Admin Index</h1>
      <div className="controls">
        <button type="button" className="account-action-btn" onClick={() => { window.location.href = "/"; }}>
          Back to Classes
        </button>
        <button type="button" className="account-action-btn" onClick={currentUser ? handleSignOut : handleSignIn}>
          <UserIcon />
          <span>{currentUser ? "Sign out" : "Sign in"}</span>
        </button>
      </div>
    </header>
    <div className="identity-status" style={{ margin: "0 0 12px" }}>{authStatus}</div>
    {!currentUser && <div style={{ color: "#4b5563" }}>Sign in with an admin account to access admin tools.</div>}
    {currentUser && !adminEnabled && <div style={{ color: "#b91c1c" }}>This account does not have admin access.</div>}
    {currentUser && adminEnabled && (
      <div style={{ border: "1px solid #e5e7eb", borderRadius: "8px", padding: "12px", display: "flex", gap: "10px", flexWrap: "wrap" }}>
        <button
          type="button"
          onClick={() => { window.location.href = "/voice-admin"; }}
          style={{ borderRadius: "14px", border: "1px solid #ddd", padding: "8px 12px", background: "#fff" }}
        >
          Teacher & Student Records
        </button>
        <button
          type="button"
          onClick={() => { window.location.href = "/teacher-courses"; }}
          style={{ borderRadius: "14px", border: "1px solid #ddd", padding: "8px 12px", background: "#fff" }}
        >
          Teacher Workspace
        </button>
      </div>
    )}
  </div>
);
