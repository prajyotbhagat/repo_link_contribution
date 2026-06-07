import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { fetchRepo, fetchRecentIssues, starRepo, unstarRepo } from '../api';
import { useAuth } from '../contexts/AuthContext';
import AuthPanel from '../components/AuthPanel';
import ChatDrawer from '../components/ChatDrawer';
import RepoAgentDrawer from '../components/RepoAgentDrawer';

function fmt(n) { return n >= 1000 ? (n / 1000).toFixed(1) + 'k' : String(n ?? 0); }


function issueAge(days) {
  if (days === 0) return 'opened today';
  if (days === 1) return 'opened 1 day ago';
  return `opened ${days} days ago`;
}

export default function RepoDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [repo, setRepo] = useState(null);
  const [issues, setIssues] = useState([]);
  const [loading, setLoading] = useState(true);
  const [authMsg, setAuthMsg] = useState({ text: '', type: '' });
  const [chatIssue, setChatIssue] = useState(null);
  const [showAgentDrawer, setShowAgentDrawer] = useState(false);

  useEffect(() => {
    Promise.all([fetchRepo(id), fetchRecentIssues(id)])
      .then(([r, i]) => { setRepo(r); setIssues(i.issues || []); })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [id]);

  const toggleStar = async () => {
    if (!user) { setAuthMsg({ text: 'Please login first to star this repository.', type: 'error' }); return; }
    try {
      if (repo.is_starred) { await unstarRepo(id); setRepo(r => ({ ...r, is_starred: false })); setAuthMsg({ text: 'Removed from notifications.', type: 'success' }); }
      else { await starRepo(id); setRepo(r => ({ ...r, is_starred: true })); setAuthMsg({ text: 'Added to notifications!', type: 'success' }); }
    } catch (e) { setAuthMsg({ text: e.message, type: 'error' }); }
  };

  const openChat = (issue) => {
    if (!user) { setAuthMsg({ text: 'Please login first to use the Beginner Guide.', type: 'error' }); return; }
    setChatIssue(issue);
  };

  const openAgent = () => {
    if (!user) { setAuthMsg({ text: 'Please login first to talk to the codebase.', type: 'error' }); return; }
    setShowAgentDrawer(true);
  };

  if (loading) return <main className="page"><div className="loader"><div className="loader-spinner" /><p>Loading…</p></div></main>;

  return (
    <>
      <main className="page">
        <a className="back-link" onClick={() => navigate('/')} style={{ cursor: 'pointer' }}>← Back to search</a>
        <AuthPanel authMsg={authMsg} setAuthMsg={setAuthMsg} />

        {repo && (
          <section className="hero">
            <div className="hero-top">
              <div>
                <div className="repo-kicker">Repository Overview</div>
                <h1 className="repo-name">{repo.full_name}</h1>
                <div className="repo-owner">{repo.owner}</div>
              </div>
              <div className="score-badge">
                <strong>{Number(repo.final_score || 0).toFixed(1)}</strong>
                <span>AI Score</span>
              </div>
            </div>
            <p className="repo-description">{repo.description || 'No description available.'}</p>
            <div className="hero-actions">
              <button className={`detail-star-btn ${repo.is_starred ? 'active' : ''}`} onClick={toggleStar}>
                {repo.is_starred ? '★ Watching for issue emails' : '☆ Star for issue emails'}
              </button>
              <button className="btn btn-sm btn-outline" style={{ marginLeft: '0.5rem' }} onClick={openAgent}>
                Talk to Codebase 🤖
              </button>
              <a className="btn btn-sm btn-outline" href={repo.repo_url} target="_blank" rel="noopener noreferrer"
                style={{ textDecoration: 'none', whiteSpace: 'nowrap', marginLeft: '0.5rem' }}>Open on GitHub</a>
            </div>
            <div className="meta-row" style={{ marginTop: '1rem' }}>
              {repo.language && <span className="pill">⚙ {repo.language}</span>}
              <span className="pill">⭐ {fmt(repo.stars)}</span>
              <span className="pill">🍴 {fmt(repo.forks)}</span>
              <span className="pill">👥 {fmt(repo.contributors_count)}</span>
              <span className="pill">🐛 {fmt(repo.open_issues)} open issues</span>
            </div>
            <div className="topics" style={{ marginTop: '0.75rem' }}>
              {(repo.topics || []).map(t => <span key={t} className="topic">{t}</span>)}
            </div>
          </section>
        )}

        <section className="section">
          <div className="section-head">
            <div>
              <h2>Recent Issues</h2>
              <p>Open issues from the last 5 days for this repository.</p>
            </div>
          </div>
          {issues.length === 0 ? (
            <div className="empty">No open issues were created in the last 5 days.</div>
          ) : (
            <div className="issues-list">
              {issues.map(issue => (
                <article key={issue.id} className="issue-card">
                  <div className="issue-card-header">
                    <a className="issue-title" href={issue.issue_url} target="_blank" rel="noopener noreferrer">
                      #{issue.github_issue_number} {issue.title}
                    </a>
                    <button className="chat-btn" onClick={() => openChat(issue)}>Guide for Beginner 💬</button>
                  </div>
                  <div className="issue-meta">
                    <span className="issue-age">{issueAge(issue.days_ago)}</span>
                    {(issue.labels || []).map(label => {
                      const cls = label.toLowerCase().includes('bug') ? 'bug' : label.toLowerCase().includes('good first') ? 'gfi' : '';
                      return <span key={label} className={`label-chip ${cls}`}>{label}</span>;
                    })}
                  </div>
                  {issue.ai_summary && <div className="summary">{issue.ai_summary}</div>}
                </article>
              ))}
            </div>
          )}
        </section>
      </main>

      {chatIssue && <ChatDrawer issue={chatIssue} onClose={() => setChatIssue(null)} />}
      {showAgentDrawer && <RepoAgentDrawer repo={repo} onClose={() => setShowAgentDrawer(false)} />}
    </>
  );
}
