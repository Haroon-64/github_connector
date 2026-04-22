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

  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);
  const showToast = (message: string, type: 'success' | 'error') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  };

  const [activeReviewPr, setActiveReviewPr] = useState<any>(null);
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

  const submitReview = async (e: SyntheticEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!activeReviewPr) return;
    
    setSubmittingReview(true);
    try {
      await axios.post(`/github/repos/${owner}/${repo}/pulls/${activeReviewPr.value}/reviews`, {
        event: reviewAction,
        body: reviewBody
      });
      showToast('Review submitted successfully!', 'success');
      setActiveReviewPr(null);
      setReviewBody('');
      setReviewAction('COMMENT');
    } catch (err: any) {
      console.error(err);
      showToast('Failed to submit review: ' + (err.response?.data?.detail || err.message), 'error');
    } finally {
      setSubmittingReview(false);
    }
  };

  if (loading) return <div style={{ color: 'var(--text-secondary)', padding: '2rem' }}>Loading dashboard...</div>;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '40px' }}>
        <div>
          <h1 style={{ fontSize: '2.5rem', marginBottom: '8px' }}>Dashboard</h1>
          <p style={{ color: 'var(--text-secondary)' }}>Welcome back, {user?.username}!</p>
        </div>
        <button onClick={handleLogout} className="glass-panel" style={{ padding: '8px 16px', background: 'transparent', color: 'var(--text-secondary)', border: '1px solid var(--border-glass)', cursor: 'pointer', borderRadius: '8px' }}>
          Sign Out
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '32px', position: 'relative' }}>
        
        {/* Repo Selection Form */}
        <div className="glass-panel" style={{ padding: '32px', height: 'fit-content' }}>
          <h2 style={{ fontSize: '1.25rem', marginBottom: '24px' }}>Load Pull Requests</h2>
          <form onSubmit={fetchPrs} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '8px', color: 'var(--text-secondary)', fontSize: '0.875rem' }}>Repository Owner</label>
              <input 
                type="text" 
                value={owner}
                onChange={e => setOwner(e.target.value)}
                placeholder="e.g. facebook"
                style={{ width: '100%', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-glass)', background: 'rgba(0,0,0,0.2)', color: 'white', outline: 'none' }}
              />
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: '8px', color: 'var(--text-secondary)', fontSize: '0.875rem' }}>Repository Name</label>
              <input 
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

        {/* PR Results or Review Flow */}
        <div className="glass-panel" style={{ padding: '32px' }}>
          {!activeReviewPr ? (
            <>
              <h2 style={{ fontSize: '1.25rem', marginBottom: '24px', display: 'flex', justifyContent: 'space-between' }}>
                Available for Review
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
                        onClick={() => setActiveReviewPr(pr)}
                        className="btn-primary" 
                        style={{ padding: '6px 16px', fontSize: '0.875rem' }}
                      >
                        Start Review
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </>
          ) : (
            <>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
                <h2 style={{ fontSize: '1.25rem' }}>Reviewing {activeReviewPr.label}</h2>
                <button onClick={() => setActiveReviewPr(null)} style={{ background: 'transparent', color: 'var(--text-secondary)', border: 'none', cursor: 'pointer' }}>Cancel</button>
              </div>

              <form onSubmit={submitReview} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div>
                  <label style={{ display: 'block', marginBottom: '8px', color: 'var(--text-secondary)', fontSize: '0.875rem' }}>Decision</label>
                  <select 
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
                  <label style={{ display: 'block', marginBottom: '8px', color: 'var(--text-secondary)', fontSize: '0.875rem' }}>Feedback / Comments</label>
                  <textarea 
                    rows={5}
                    value={reviewBody}
                    onChange={e => setReviewBody(e.target.value)}
                    placeholder="Leave your review comments here..."
                    style={{ width: '100%', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-glass)', background: 'rgba(0,0,0,0.2)', color: 'white', outline: 'none', resize: 'vertical' }}
                  />
                </div>

                <div style={{ display: 'flex', gap: '12px', marginTop: '16px' }}>
                  <button type="submit" className="btn-primary" style={{ flex: 1 }} disabled={submittingReview}>
                    {submittingReview ? 'Submitting...' : 'Submit Review'}
                  </button>
                </div>
              </form>
            </>
          )}
        </div>

      </div>

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
