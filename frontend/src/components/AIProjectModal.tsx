import React, { useState } from "react";
import { Sparkles, Download, Loader2, X } from "lucide-react";

export interface AIProjectModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export interface ProjectFormData {
  category: string;
  tech_stack: string;
  difficulty: string;
  description: string;
}

export interface ProjectSuggestion {
  id?: number | string;
  title: string;
  summary: string;
  category: string;
  difficulty: string;
  target_audience: string;
}

export const AIProjectModal: React.FC<AIProjectModalProps> = ({ isOpen, onClose }) => {
  const [step, setStep] = useState<number>(1);
  const [loading, setLoading] = useState<boolean>(false);

  const [formData, setFormData] = useState<ProjectFormData>({
    category: "Web Development",
    tech_stack: "React, FastAPI, PostgreSQL",
    difficulty: "Intermediate",
    description: "",
  });

  const [suggestions, setSuggestions] = useState<ProjectSuggestion[]>([]);
  const [selectedProject, setSelectedProject] = useState<ProjectSuggestion | null>(null);

  if (!isOpen) return null;

  // Step 1: Submit Form -> Fetch Suggestions
  const handleFetchSuggestions = async (e: React.FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await fetch("/api/ai-projects/suggest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData),
      });

      if (!res.ok) throw new Error("Failed to connect to backend");

      const data: { projects: ProjectSuggestion[] } = await res.json();
      setSuggestions(data.projects || []);
      setStep(2);
    } catch (err) {
      alert("Failed to generate project suggestions.");
    } finally {
      setLoading(false);
    }
  };

  // Step 2: Download PDF for selected project
  const handleDownloadPDF = async (project: ProjectSuggestion): Promise<void> => {
    setSelectedProject(project);
    setLoading(true);
    try {
      const response = await fetch("/api/ai-projects/generate-proposal-pdf", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(project),
      });

      if (!response.ok) throw new Error("Failed to download PDF");

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `Proposal_${project.title.replace(/\s+/g, "_")}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert("Failed to generate PDF proposal.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.overlay}>
      <div style={styles.modal}>
        {/* Header */}
        <div style={styles.modalHeader}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <Sparkles color="#a78bfa" size={20} />
            <h3 style={{ margin: 0, color: "var(--text-main, #f8fafc)", fontSize: 18, fontWeight: 600 }}>
              AI Project Generator
            </h3>
          </div>
          <button onClick={onClose} style={styles.closeBtn} type="button" aria-label="Close modal">
            <X size={18} />
          </button>
        </div>

        {/* STEP 1: INPUT FORM */}
        {step === 1 && (
          <form onSubmit={handleFetchSuggestions} style={styles.form}>
            <label style={styles.label}>Category</label>
            <select
              style={styles.input}
              value={formData.category}
              onChange={(e: React.ChangeEvent<HTMLSelectElement>) =>
                setFormData({ ...formData, category: e.target.value })
              }
            >
              <option value="Web Development" style={styles.option}>Web Development</option>
              <option value="AI & Machine Learning" style={styles.option}>AI & Machine Learning</option>
              <option value="Mobile App Development" style={styles.option}>Mobile App Development</option>
              <option value="Cloud & DevOps" style={styles.option}>Cloud & DevOps</option>
              <option value="Data Science" style={styles.option}>Data Science</option>
              <option value="Data Analytics" style={styles.option}>Data Analytics</option>
            </select>

            <label style={styles.label}>Preferred Tech Stack</label>
            <input
              style={styles.input}
              type="text"
              placeholder="e.g. React, Python, Docker"
              value={formData.tech_stack}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                setFormData({ ...formData, tech_stack: e.target.value })
              }
            />

            <label style={styles.label}>Difficulty Level</label>
            <select
              style={styles.input}
              value={formData.difficulty}
              onChange={(e: React.ChangeEvent<HTMLSelectElement>) =>
                setFormData({ ...formData, difficulty: e.target.value })
              }
            >
              <option value="Beginner" style={styles.option}>Beginner</option>
              <option value="Intermediate" style={styles.option}>Intermediate</option>
              <option value="Advanced" style={styles.option}>Advanced</option>
            </select>

            <label style={styles.label}>Additional Requirements / Ideas (Optional)</label>
            <textarea
              style={{ ...styles.input, height: 75, resize: "vertical" }}
              placeholder="e.g. Must include real-time chat feature..."
              value={formData.description}
              onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) =>
                setFormData({ ...formData, description: e.target.value })
              }
            />

            <button type="submit" disabled={loading} style={styles.submitBtn}>
              {loading ? <Loader2 style={{ animation: "spin 1s linear infinite" }} size={18} /> : "Generate Ideas"}
            </button>
          </form>
        )}

        {/* STEP 2: CHOOSE A PROJECT */}
        {step === 2 && (
          <div>
            <p style={{ fontSize: 13, color: "var(--text-muted, #94a3b8)", marginTop: 0, marginBottom: 16 }}>
              Select a project idea to generate and download a detailed PDF proposal:
            </p>
            <div style={styles.cardList}>
              {suggestions.map((proj, idx) => (
                <div key={proj.id || idx} style={styles.projectCard}>
                  <h4 style={{ margin: "0 0 6px 0", color: "var(--text-main, #f8fafc)", fontSize: 15 }}>
                    {proj.title}
                  </h4>
                  <p style={{ fontSize: 13, color: "var(--text-muted, #94a3b8)", margin: "0 0 14px 0", lineHeight: 1.4 }}>
                    {proj.summary}
                  </p>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={styles.badge}>{proj.difficulty}</span>
                    <button
                      onClick={() => handleDownloadPDF(proj)}
                      disabled={loading && selectedProject?.title === proj.title}
                      style={styles.downloadBtn}
                      type="button"
                    >
                      {loading && selectedProject?.title === proj.title ? (
                        <Loader2 size={14} style={{ animation: "spin 1s linear infinite" }} />
                      ) : (
                        <>
                          <Download size={14} /> Download Proposal PDF
                        </>
                      )}
                    </button>
                  </div>
                </div>
              ))}
            </div>
            <button onClick={() => setStep(1)} style={styles.backBtn} type="button">
              ← Back to Form
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default AIProjectModal;

const styles: Record<string, React.CSSProperties> = {
  overlay: {
    position: "fixed",
    inset: 0,
    backgroundColor: "rgba(0, 0, 0, 0.75)",
    backdropFilter: "blur(4px)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    zIndex: 1000,
  },
  modal: {
    width: "100%",
    maxWidth: "520px",
    backgroundColor: "var(--bg-card, #0f172a)",
    border: "1px solid var(--border-color, #1e293b)",
    borderRadius: "16px",
    padding: "24px",
    boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.5)",
  },
  modalHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: "20px",
  },
  closeBtn: {
    background: "none",
    border: "none",
    cursor: "pointer",
    color: "var(--text-muted, #94a3b8)",
    padding: 4,
    borderRadius: "6px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  },
  form: {
    display: "flex",
    flexDirection: "column",
    gap: "14px",
  },
  label: {
    fontSize: "12px",
    fontWeight: 600,
    textTransform: "uppercase",
    letterSpacing: "0.05em",
    color: "var(--text-muted, #94a3b8)",
  },
  input: {
    padding: "10px 14px",
    borderRadius: "8px",
    border: "1px solid var(--border-color, #334155)",
    backgroundColor: "var(--bg-item, #1e293b)",
    color: "var(--text-main, #f8fafc)",
    fontFamily: "inherit",
    fontSize: "14px",
    outline: "none",
  },
  option: {
    backgroundColor: "#1e293b",
    color: "#f8fafc",
  },
  submitBtn: {
    marginTop: "10px",
    padding: "12px",
    backgroundColor: "#6366f1",
    color: "#ffffff",
    border: "none",
    borderRadius: "8px",
    fontWeight: 600,
    fontSize: "14px",
    cursor: "pointer",
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    boxShadow: "0 4px 12px rgba(99, 102, 241, 0.3)",
  },
  cardList: {
    display: "flex",
    flexDirection: "column",
    gap: "12px",
    maxHeight: "360px",
    overflowY: "auto",
    margin: "16px 0",
    paddingRight: "4px",
  },
  projectCard: {
    border: "1px solid var(--border-color, #1e293b)",
    padding: "16px",
    borderRadius: "10px",
    backgroundColor: "var(--bg-item, #1e293b)",
  },
  badge: {
    fontSize: "11px",
    padding: "4px 10px",
    backgroundColor: "rgba(99, 102, 241, 0.15)",
    color: "#a5b4fc",
    borderRadius: "20px",
    fontWeight: 600,
    border: "1px solid rgba(99, 102, 241, 0.3)",
  },
  downloadBtn: {
    display: "flex",
    alignItems: "center",
    gap: 6,
    padding: "8px 14px",
    backgroundColor: "#059669",
    color: "#ffffff",
    border: "none",
    borderRadius: "6px",
    fontSize: "12px",
    fontWeight: 600,
    cursor: "pointer",
  },
  backBtn: {
    background: "none",
    border: "none",
    color: "var(--text-muted, #94a3b8)",
    fontSize: "13px",
    fontWeight: 500,
    cursor: "pointer",
    padding: 0,
    marginTop: 4,
  },};