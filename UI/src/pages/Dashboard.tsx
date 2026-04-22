import { useEffect, useState, type SyntheticEvent } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';

export default function Dashboard() {
  const navigate = useNavigate();
  const [user, setUser] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  
  const [owner, setOwner] = useState('');
  const [repo, setRepo] = useState('');
  const [prs, setPrs] = useState<any[]>([]);
  const [loadingPrs, setLoadingPrs] = useState(false);

  const [activeTab, setActiveTab] = useState<'explorer' | 'inbox'>('explorer');
  const [tasks, setTasks] = useState<any[]>([]);
  const [loadingTasks, setLoadingTasks] = useState(false);

  // Toast State
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);
  const showToast = (message: string, type: 'success' | 'error') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  };

  const [activeReviewTask, setActiveReviewTask] = useState<any>(null);
  const [reviewAction, setReviewAction] = useState('COMMENT');
  const [reviewBody, setReviewBody] = useState('');
  const [submittingReview, setSubmittingReview] = useState(false);

  useEffect(() => {
    axios.get('/auth/me')
      .then(res => {
        setUser(res.data);
        setLoading(false);
      })
      .catch(() => {
        navigate('/');
      });
  }, [navigate]);

  useEffect(() => {
    if (activeTab === 'inbox' && user) {
      fetchTasks();
    }
  }, [activeTab, user]);

  const handleLogout = async () => {
    try {
      await axios.post('/auth/logout');
      navigate('/');
    } catch {
      navigate('/');
    }
  };

  const fetchPrs = async (e: SyntheticEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!owner || !repo) return;
    
    setLoadingPrs(true);
    try {
      const res = await axios.get(`/github/repos/${owner}/${repo}/pulls/camunda-options`);
      setPrs(res.data.prOptions || []);
    } catch (err) {
      console.error("Failed to fetch PRs", err);
      showToast("Failed to fetch PRs. Ensure repository exists and you have access.", "error");
    } finally {
      setLoadingPrs(false);
    }
  };

  const fetchTasks = async () => {
    setLoadingTasks(true);
    try {
      const res = await axios.get('/camunda/tasks');
      const taskList = Array.isArray(res.data) ? res.data : (res.data.items || res.data.tasks || []);
      setTasks(taskList);
    } catch (err) {
      console.error("Failed to fetch Tasks", err);
      showToast("Failed to fetch Camunda Tasks.", "error");
    } finally {
      setLoadingTasks(false);
    }
  };

  const orchestrateReview = async (pr: any) => {
    try {
      await axios.post('/camunda/process/start', {
        owner,
        repo,
        pull_number: pr.value
      });
      showToast(`Process orchestration started for ${pr.label}!`, 'success');
      setTimeout(() => setActiveTab('inbox'), 1000);
    } catch (err: any) {
      showToast('Failed to orchestrate process: ' + (err.response?.data?.detail || err.message), 'error');
    }
  };

  const submitReview = async (e: SyntheticEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!activeReviewTask) return;
    
    setSubmittingReview(true);
    try {
      const taskVars = activeReviewTask.variables || [];
      const getVar = (name: string) => {
        if (Array.isArray(taskVars)) {
          const v = taskVars.find((v: any) => v.name === name);
          return v ? v.value : null;
        } else {
          return taskVars[name];
        }
      };

      const prOwner = getVar('owner') || owner || "unknown";
      const prRepo = getVar('repo') || repo || "unknown";
      const pullNum = getVar('pull_number');

      if (!pullNum) {
        throw new Error("Cannot determine pull_number from task variables.");
      }

      await axios.post(`/github/repos/${prOwner}/${prRepo}/pulls/${pullNum}/reviews`, {
        event: reviewAction,
        body: reviewBody
      });

      await axios.post(`/camunda/tasks/${activeReviewTask.userTaskKey}/complete`, {
        decision: reviewAction,
        comment: reviewBody
      });

      showToast('Review submitted and Task completed successfully!', 'success');
      setActiveReviewTask(null);
      setReviewBody('');
      setReviewAction('COMMENT');
      fetchTasks();
    } catch (err: any) {
      console.error(err);
      showToast('Failed to complete task: ' + (err.response?.data?.detail || err.message), 'error');
    } finally {
      setSubmittingReview(false);
    }
  };

  if (loading) return <div style={{ color: 'var(--text-secondary)', padding: '2rem' }}>Loading dashboard...</div>;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <h1 style={{ fontSize: '2.5rem', marginBottom: '8px' }}>Dashboard</h1>
          <p style={{ color: 'var(--text-secondary)' }}>Welcome back, {user?.username}!</p>
        </div>
        <button onClick={handleLogout} className="glass-panel" style={{ padding: '8px 16px', background: 'transparent', color: 'var(--text-secondary)', border: '1px solid var(--border-glass)', cursor: 'pointer', borderRadius: '8px' }}>
          Sign Out
        </button>
      </div>

      <div style={{ display: 'flex', gap: '16px', marginBottom: '32px', borderBottom: '1px solid var(--border-glass)', paddingBottom: '16px' }}>
        <button 
          onClick={() => setActiveTab('explorer')}
          className="btn-primary" 
          style={{ background: activeTab === 'explorer' ? 'var(--accent-gradient)' : 'transparent', border: '1px solid var(--border-glass)', color: activeTab === 'explorer' ? 'white' : 'var(--text-secondary)' }}>
          PR Explorer
        </button>
        <button 
          onClick={() => setActiveTab('inbox')}
          className="btn-primary" 
          style={{ background: activeTab === 'inbox' ? 'var(--accent-gradient)' : 'transparent', border: '1px solid var(--border-glass)', color: activeTab === 'inbox' ? 'white' : 'var(--text-secondary)' }}>
          My Task Inbox {tasks.length > 0 && `(${tasks.length})`}
        </button>
      </div>

      {activeTab === 'explorer' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '32px', position: 'relative' }}>
          {/* Repo Selection Form */}
          <div className="glass-panel" style={{ padding: '32px', height: 'fit-content' }}>
            <h2 style={{ fontSize: '1.25rem', marginBottom: '24px' }}>Load Pull Requests</h2>
            <form onSubmit={fetchPrs} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div>
                <label htmlFor="repo-owner" style={{ display: 'block', marginBottom: '8px', color: 'var(--text-secondary)', fontSize: '0.875rem' }}>Repository Owner</label>
                <input 
                  id="repo-owner"
                  type="text" 
                  value={owner}
                  onChange={e => setOwner(e.target.value)}
                  placeholder="e.g. facebook"
                  style={{ width: '100%', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-glass)', background: 'rgba(0,0,0,0.2)', color: 'white', outline: 'none' }}
                />
              </div>
              <div>
                <label htmlFor="repo-name" style={{ display: 'block', marginBottom: '8px', color: 'var(--text-secondary)', fontSize: '0.875rem' }}>Repository Name</label>
                <input 
                  id="repo-name"
                  type="text" 
                  value={repo}
                  onChange={e => setRepo(e.target.value)}
                  placeholder="e.g. react"
                  style={{ width: '100%', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-glass)', background: 'rgba(0,0,0,0.2)', color: 'white', outline: 'none' }}
                />
              </div>
              <button type="submit" className="btn-primary" style={{ width: '100%', marginTop: '8px' }} disabled={loadingPrs}>
                {loadingPrs ? 'Loading...' : 'Fetch Active PRs'}
              </button>
            </form>
          </div>

          {/* PR Results */}
          <div className="glass-panel" style={{ padding: '32px' }}>
            <h2 style={{ fontSize: '1.25rem', marginBottom: '24px', display: 'flex', justifyContent: 'space-between' }}>
              <span>Available PRs</span>
              {prs.length > 0 && <span style={{ background: 'var(--accent-primary)', padding: '2px 10px', borderRadius: '12px', fontSize: '0.875rem' }}>{prs.length}</span>}
            </h2>
            
            {prs.length === 0 && !loadingPrs ? (
              <div style={{ textAlign: 'center', padding: '40px 0', color: 'var(--text-tertiary)' }}>
                No pull requests loaded. Enter a repository to begin.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {prs.map(pr => (
                  <div key={pr.value} style={{ padding: '16px', borderRadius: '8px', background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border-glass)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ fontWeight: 500 }}>{pr.label}</div>
                    <button 
                      onClick={() => orchestrateReview(pr)}
                      className="btn-primary" 
                      style={{ padding: '6px 16px', fontSize: '0.875rem' }}
                    >
                      Orchestrate
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === 'inbox' && (
        <div style={{ position: 'relative' }}>
          <div className="glass-panel" style={{ padding: '32px' }}>
            {activeReviewTask ? (
              <>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
                  <h2 style={{ fontSize: '1.25rem' }}>Executing Task: {activeReviewTask.name || activeReviewTask.id}</h2>
                  <button onClick={() => setActiveReviewTask(null)} style={{ background: 'transparent', color: 'var(--text-secondary)', border: 'none', cursor: 'pointer' }}>Back to Inbox</button>
                </div>

                <form onSubmit={submitReview} style={{ display: 'flex', flexDirection: 'column', gap: '16px', maxWidth: '600px' }}>
                  <div>
                    <label htmlFor="review-decision" style={{ display: 'block', marginBottom: '8px', color: 'var(--text-secondary)', fontSize: '0.875rem' }}>Decision</label>
                    <select 
                      id="review-decision"
                      value={reviewAction} 
                      onChange={e => setReviewAction(e.target.value)}
                      style={{ width: '100%', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-glass)', background: 'rgba(0,0,0,0.5)', color: 'white', outline: 'none' }}
                    >
                      <option value="COMMENT">Comment Only</option>
                      <option value="APPROVE">Approve</option>
                      <option value="REQUEST_CHANGES">Request Changes</option>
                    </select>
                  </div>

                  <div>
                    <label htmlFor="review-comments" style={{ display: 'block', marginBottom: '8px', color: 'var(--text-secondary)', fontSize: '0.875rem' }}>Feedback / Comments</label>
                    <textarea 
                      id="review-comments"
                      rows={5}
                      value={reviewBody}
                      onChange={e => setReviewBody(e.target.value)}
                      placeholder="Leave your review comments here..."
                      style={{ width: '100%', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-glass)', background: 'rgba(0,0,0,0.2)', color: 'white', outline: 'none', resize: 'vertical' }}
                    />
                  </div>

                  <div style={{ display: 'flex', gap: '12px', marginTop: '16px' }}>
                    <button type="submit" className="btn-primary" style={{ flex: 1 }} disabled={submittingReview}>
                      {submittingReview ? 'Submitting & Completing...' : 'Submit & Complete'}
                    </button>
                  </div>
                </form>
              </>
            ) : (
              <>
                <h2 style={{ fontSize: '1.25rem', marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span>My Assigned Tasks</span>
                  <button onClick={fetchTasks} className="btn-primary" style={{ padding: '4px 12px', fontSize: '0.75rem', background: 'transparent', border: '1px solid var(--border-glass)' }}>
                    {loadingTasks ? 'Refreshing...' : 'Refresh Inbox'}
                  </button>
                </h2>
                
                {tasks.length === 0 && !loadingTasks ? (
                  <div style={{ textAlign: 'center', padding: '40px 0', color: 'var(--text-tertiary)' }}>
                    Your inbox is entirely clear!
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    {tasks.map((task: any) => (
                      <div key={task.id} style={{ padding: '16px', borderRadius: '8px', background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border-glass)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div>
                          <div style={{ fontWeight: 500, marginBottom: '4px' }}>Task: {task.name || task.id}</div>
                          <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Status: {task.taskState || 'ACTIVE'} | Process: {task.processName || 'pr_review_v2'}</div>
                        </div>
                        <button 
                          onClick={() => setActiveReviewTask(task)}
                          className="btn-primary" 
                          style={{ padding: '6px 16px', fontSize: '0.875rem' }}
                        >
                          Work Task
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}

      {toast && (
        <div style={{
          position: 'fixed',
          bottom: '24px',
          right: '24px',
          padding: '16px 24px',
          borderRadius: '8px',
          background: toast.type === 'success' ? '#10b981' : '#ef4444',
          color: 'white',
          boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.4)',
          zIndex: 1000,
          fontWeight: 500,
          animation: 'slideUp 0.3s ease-out'
        }}>
          {toast.message}
        </div>
      )}
    </div>
  );
}
