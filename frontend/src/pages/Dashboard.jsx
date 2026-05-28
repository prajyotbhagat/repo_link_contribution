import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { fetchRepos, starRepo, unstarRepo } from '../api';
import AuthPanel from '../components/AuthPanel';
import { useAuth } from '../contexts/AuthContext';

function fmt(n) { return n >= 1000 ? (n / 1000).toFixed(1) + 'k' : String(n ?? 0); }
function pct(v) { return Math.min(100, Math.max(0, v || 0)).toFixed(1); }
function getInitial(name) { return (name || '?')[0].toUpperCase(); }
function getScoreColor(score) {
  if (score >= 70) return '#10b981';
  if (score >= 45) return '#f59e0b';
  return '#ef4444';
}

const SORT_LABELS = {
  final_score: 'AI Score',
  stars: 'Stars',
  activity_score: 'Activity',
  beginner_score: 'Beginner Friendly',
  doc_score: 'Documentation',
};

function RepoCard({ repo, onStar, user }) {
  const navigate = useNavigate();
  const score = (repo.final_score || 0).toFixed(1);
  const scoreColor = getScoreColor(repo.final_score);
  const issueCount = repo.recent_issues_count || 0;
  const badgeCls = issueCount === 0 ? 'zero' : '';
  const starred = !!repo.is_starred;
  const topics = (repo.topics || []).slice(0, 3);

  return (
    <div className="card">
      <div className="card-header">
        <div className="repo-icon">{getInitial(repo.name)}</div>
        <div className="card-title-area">
          <div className="card-title" title={repo.full_name}>{repo.full_name}</div>
          <div className="card-owner">{repo.owner}</div>
        </div>
        <div className="repo-actions">
          <button
            className={`star-btn ${starred ? 'active' : ''}`}
            title={starred ? 'Stop notifications' : 'Get issue notifications'}
            onClick={e => { e.stopPropagation(); onStar(repo.id, starred); }}
          >★</button>
          <div
            className="final-score-badge"
            style={{ color: scoreColor, borderColor: scoreColor + '40', background: scoreColor + '18' }}
            title="AI Final Score"
          >{score}</div>
        </div>
      </div>

      <div className="card-desc">{repo.description || 'No description available.'}</div>

      <div className="metrics">
        {[
          { label: 'Activity', val: repo.activity_score, cls: 'bar-activity' },
          { label: 'Beginner', val: repo.beginner_score, cls: 'bar-beginner' },
          { label: 'Docs', val: repo.doc_score, cls: 'bar-doc' },
          { label: 'Popularity', val: repo.popularity_score, cls: 'bar-popularity' },
          { label: 'Maintenance', val: repo.maintenance_score, cls: 'bar-maintenance' },
        ].map(({ label, val, cls }) => (
          <div className="metric" key={label}>
            <span className="metric-label">{label}</span>
            <div className="metric-bar-bg">
              <div className={`metric-bar ${cls}`} style={{ width: `${pct(val)}%` }} />
            </div>
            <span className="metric-val">{pct(val)}</span>
          </div>
        ))}
      </div>

      <a className="issues-toggle" onClick={() => navigate(`/repo/${repo.id}`)} style={{ cursor: 'pointer' }}>
        <span>🐛 Recent Issues</span>
        <span className={`issues-badge ${badgeCls}`}>{issueCount} in last 5 days</span>
        <span className="chevron">→</span>
      </a>

      <div className="card-footer">
        {repo.language && <span className="tag tag-lang">{repo.language}</span>}
        <span className="tag tag-stars">⭐ {fmt(repo.stars)}</span>
        {repo.contributors_count ? <span className="tag tag-contribs">👥 {fmt(repo.contributors_count)}</span> : null}
        {topics.map(t => <span key={t} className="tag tag-topic">{t}</span>)}
        <a className="card-link" href={repo.repo_url} target="_blank" rel="noopener noreferrer"
          onClick={e => e.stopPropagation()}>View →</a>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const { user } = useAuth();
  const [repos, setRepos] = useState([]);
  const [query, setQuery] = useState('');
  const [language, setLanguage] = useState('');
  const [sortKey, setSortKey] = useState('final_score');
  const [mode, setMode] = useState('Top Repos');
  const [loading, setLoading] = useState(true);
  const [authMsg, setAuthMsg] = useState({ text: '', type: '' });

  const load = async (q = query, lang = language, sk = sortKey, newMode) => {
    setLoading(true);
    try {
      const data = await fetchRepos(q, lang);
      const sorted = [...data].sort((a, b) => (b[sk] || 0) - (a[sk] || 0));
      setRepos(sorted);
      setMode(newMode || (q ? `AI: "${q}"` : lang ? `Language: ${lang}` : 'Top Repos'));
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  useEffect(() => { load('', '', 'final_score', 'Top Repos'); }, []);

  const handleSortChange = (sk) => {
    setSortKey(sk);
    const sorted = [...repos].sort((a, b) => (b[sk] || 0) - (a[sk] || 0));
    setRepos(sorted);
  };

  const handleStar = async (repoId, currentlyStarred) => {
    if (!user) { setAuthMsg({ text: 'Login or register first to star repositories.', type: 'error' }); return; }
    try {
      if (currentlyStarred) await unstarRepo(repoId);
      else await starRepo(repoId);
      setRepos(rs => rs.map(r => r.id === repoId ? { ...r, is_starred: !currentlyStarred } : r));
      setAuthMsg({ text: currentlyStarred ? 'Removed from notifications.' : 'Added to notifications!', type: 'success' });
    } catch (e) { setAuthMsg({ text: e.message, type: 'error' }); }
  };

  return (
    <>
      <header>
        <div className="logo">🔭 RepoRadar</div>
        <p className="tagline">AI-powered open source discovery — find repositories that actually matter to you</p>
        <div className="search-container">
          <div className="search-row">
            <input
              className="search-input"
              placeholder="Search with AI... e.g. 'beginner friendly Python web framework'"
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && load()}
            />
            <button className="btn" onClick={() => load()}>Search</button>
          </div>
          <div className="filter-row">
            <select value={language} onChange={e => { setLanguage(e.target.value); load(query, e.target.value, sortKey); }}>
              <option value="">All Languages</option>
              {['Python', 'JavaScript', 'TypeScript', 'Go', 'Rust', 'Java', 'C++', 'C', 'Ruby', 'PHP', 'Markdown', 'Shell'].map(l => (
                <option key={l} value={l}>{l}</option>
              ))}
            </select>
            <select value={sortKey} onChange={e => handleSortChange(e.target.value)}>
              <option value="final_score">Sort: AI Score</option>
              <option value="stars">Sort: Stars</option>
              <option value="activity_score">Sort: Activity</option>
              <option value="beginner_score">Sort: Beginner Friendly</option>
              <option value="doc_score">Sort: Documentation</option>
            </select>
            <button className="btn btn-sm btn-outline" onClick={() => { setQuery(''); setLanguage(''); setSortKey('final_score'); load('', '', 'final_score', 'Top Repos'); }}>Top Repos</button>
            <button className="btn btn-sm btn-outline" onClick={() => { setQuery(''); setLanguage(''); setSortKey('final_score'); load('', '', 'final_score', 'Top Repos'); }}>Clear</button>
          </div>
        </div>
        <AuthPanel authMsg={authMsg} setAuthMsg={setAuthMsg} />
      </header>

      <main>
        {!loading && repos.length > 0 && (
          <div className="stats-bar">
            <div className="stat-pill">Showing <span>{repos.length}</span> repositories</div>
            <div className="stat-pill">Mode: <span>{mode}</span></div>
            <div className="sort-info">Sorted by {SORT_LABELS[sortKey] || 'AI Score'}</div>
          </div>
        )}

        {loading ? (
          <div className="loader" style={{ gridColumn: '1/-1' }}>
            <div className="spinner" />
            <span style={{ color: 'var(--muted)', fontSize: '.9rem' }}>Searching with AI...</span>
          </div>
        ) : repos.length === 0 ? (
          <div className="empty-state" style={{ gridColumn: '1/-1' }}>
            <h3>No repositories found</h3>
            <p>Try a different search or clear the filters.</p>
          </div>
        ) : (
          <div className="grid">
            {repos.map(repo => (
              <RepoCard key={repo.id} repo={repo} user={user} onStar={handleStar} />
            ))}
          </div>
        )}
      </main>
    </>
  );
}
