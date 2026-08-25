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
      const res = await fetch("/api/v1/ai-projects/suggest", {
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
      const response = await fetch("/api/v1/ai-projects/generate-proposal-pdf", {
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
            <Sparkles color="#8b5cf6" size={20} />
            <h3 style={{ margin: 0, color: "var(--text-main, #0f172a)" }}>AI Project Generator</h3>
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
              <option value="Web Development">Web Development</option>
              <option value="AI & Machine Learning">AI & Machine Learning</option>
              <option value="Mobile App Development">Mobile App Development</option>
              <option value="Cloud & DevOps">Cloud & DevOps</option>
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
              <option value="Beginner">Beginner</option>
              <option value="Intermediate">Intermediate</option>
              <option value="Advanced">Advanced</option>
            </select>

            <label style={styles.label}>Additional Requirements / Ideas (Optional)</label>
            <textarea
              style={{ ...styles.input, height: 70 }}
              placeholder="e.g. Must include real-time chat feature..."
              value={formData.description}
              onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) =>
                setFormData({ ...formData, description: e.target.value })
              }
            />

            <button type="submit" disabled={loading} style={styles.submitBtn}>
              {loading ? <Loader2 style={{ animation: "spin 1s linear infinite" }} /> : "Generate Ideas"}
            </button>
          </form>
        )}

        {/* STEP 2: CHOOSE A PROJECT */}
        {step === 2 && (
          <div>
            <p style={{ fontSize: 14, color: "var(--text-muted, #64748b)" }}>
              Select a project idea to view options and download a detailed PDF proposal:
            </p>
            <div style={styles.cardList}>
              {suggestions.map((proj, idx) => (
                <div key={proj.id || idx} style={styles.projectCard}>
                  <h4 style={{ margin: "0 0 4px 0", color: "var(--text-main, #0f172a)" }}>{proj.title}</h4>
                  <p style={{ fontSize: 13, color: "var(--text-muted, #64748b)", margin: "0 0 12px 0" }}>
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
              Back to Form
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
    backgroundColor: "rgba(0,0,0,0.5)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    zIndex: 1000,
  },
  modal: {
    width: "100%",
    maxWidth: "520px",
    backgroundColor: "var(--bg-card, #ffffff)",
    borderRadius: "12px",
    padding: "24px",
    boxShadow: "0 20px 25px -5px rgba(0,0,0,0.1)",
  },
  modalHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: "16px",
  },
  closeBtn: {
    background: "none",
    border: "none",
    cursor: "pointer",
    color: "var(--text-muted, #64748b)",
  },
  form: {
    display: "flex",
    flexDirection: "column",
    gap: "12px",
  },
  label: {
    fontSize: "13px",
    fontWeight: 600,
    color: "var(--text-main, #334155)",
  },
  input: {
    padding: "10px",
    borderRadius: "6px",
    border: "1px solid var(--border-color, #cbd5e1)",
    backgroundColor: "var(--bg-item, #fff)",
    color: "var(--text-main, #0f172a)",
    fontFamily: "inherit",
  },
  submitBtn: {
    marginTop: "12px",
    padding: "10px",
    backgroundColor: "#8b5cf6",
    color: "#fff",
    border: "none",
    borderRadius: "6px",
    fontWeight: 600,
    cursor: "pointer",
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
  },
  cardList: {
    display: "flex",
    flexDirection: "column",
    gap: "12px",
    maxHeight: "350px",
    overflowY: "auto",
    margin: "16px 0",
  },
  projectCard: {
    border: "1px solid var(--border-color, #e2e8f0)",
    padding: "14px",
    borderRadius: "8px",
    backgroundColor: "var(--bg-item, #f8fafc)",
  },
  badge: {
    fontSize: "11px",
    padding: "3px 8px",
    backgroundColor: "rgba(139, 92, 246, 0.15)",
    color: "#8b5cf6",
    borderRadius: "12px",
    fontWeight: 600,
  },
  downloadBtn: {
    display: "flex",
    alignItems: "center",
    gap: 6,
    padding: "6px 12px",
    backgroundColor: "#10b981",
    color: "#fff",
    border: "none",
    borderRadius: "6px",
    fontSize: "12px",
    fontWeight: 600,
    cursor: "pointer",
  },
  backBtn: {
    background: "none",
    border: "none",
    color: "var(--text-muted, #64748b)",
    fontSize: "13px",
    cursor: "pointer",
  },
};