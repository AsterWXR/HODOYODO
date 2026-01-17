import { useState, useCallback } from 'react'

function App() {
  const [selectedFile, setSelectedFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [dragging, setDragging] = useState(false)
  const [targetGender, setTargetGender] = useState(null) // 'boyfriend' or 'girlfriend'
  // 折叠状态
  const [collapsed, setCollapsed] = useState({
    girlfriend: false,
    lifestyle: false,
    body: false,
    details: false,
    reliability: false
  })

  const toggleCollapse = (key) => {
    setCollapsed(prev => ({ ...prev, [key]: !prev[key] }))
  }

  const handleFileSelect = useCallback((file) => {
    if (!file) return
    
    const validTypes = ['image/jpeg', 'image/png', 'image/webp']
    if (!validTypes.includes(file.type)) {
      setError('请上传 JPEG、PNG 或 WebP 格式的图片')
      return
    }
    
    if (file.size > 5 * 1024 * 1024) {
      setError('文件大小不能超过 5MB')
      return
    }
    
    setSelectedFile(file)
    setPreview(URL.createObjectURL(file))
    setResult(null)
    setError(null)
  }, [])

  const handleDrop = useCallback((e) => {
    e.preventDefault()
    setDragging(false)
    const file = e.dataTransfer.files[0]
    handleFileSelect(file)
  }, [handleFileSelect])

  const handleDragOver = useCallback((e) => {
    e.preventDefault()
    setDragging(true)
  }, [])

  const handleDragLeave = useCallback(() => {
    setDragging(false)
  }, [])

  const handleInputChange = useCallback((e) => {
    const file = e.target.files[0]
    handleFileSelect(file)
  }, [handleFileSelect])

  const analyzeImage = async () => {
    if (!selectedFile) return
    
    setLoading(true)
    setError(null)
    
    try {
      const formData = new FormData()
      formData.append('image', selectedFile)
      formData.append('target_gender', targetGender)
      
      const response = await fetch('/api/analyze', {
        method: 'POST',
        body: formData,
      })
      
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || '分析失败')
      }
      
      const data = await response.json()
      setResult(data)
    } catch (err) {
      setError(err.message || '网络错误，请重试')
    } finally {
      setLoading(false)
    }
  }

  // 计算综合可靠性评估
  const calculateReliability = (analysis) => {
    if (!analysis) return { level: 'unknown', label: '无法判断', summary: '' }
    
    let totalScore = 0
    let factorCount = 0
    
    const credibilityItems = analysis.credibility?.items || []
    credibilityItems.forEach(item => {
      const conf = item.confidence
      let score = conf === 'high' ? 3 : conf === 'medium' ? 2 : 1
      totalScore += score
      factorCount++
    })
    
    const person = analysis.person || {}
    if (person.detected) {
      if (person.confidence === 'high') totalScore += 3
      else if (person.confidence === 'medium') totalScore += 2
      else totalScore += 1
      factorCount++
    }
    
    const room = analysis.room_analysis || {}
    if (room.confidence === 'high') totalScore += 3
    else if (room.confidence === 'medium') totalScore += 2
    else totalScore += 1
    factorCount++
    
    const avgScore = factorCount > 0 ? totalScore / factorCount : 0
    
    let level, label, summary
    if (avgScore >= 2.5) {
      level = 'high'
      label = '可信度较高'
      summary = '综合分析显示，该照片的真实性指标较好，各项分析一致性较高。'
    } else if (avgScore >= 1.8) {
      level = 'medium'
      label = '可信度中等'
      summary = '部分指标正常，但存在一些不确定因素，建议结合其他信息综合判断。'
    } else if (avgScore >= 1) {
      level = 'low'
      label = '可信度较低'
      summary = '多项指标存在疑问，证据不足或存在异常，请谨慎对待。'
    } else {
      level = 'unknown'
      label = '无法判断'
      summary = '分析信息不足，无法给出可靠性评估。'
    }
    
    return { level, label, summary }
  }

  // 获取生活方式分析摘要
  const getLifestyleSummary = (analysis) => {
    if (!analysis) return { text: '', tags: [] }
    
    const lifestyleItems = analysis.lifestyle?.items || []
    const texts = []
    const tags = []
    
    lifestyleItems.forEach(item => {
      if (item.claim && !item.claim.includes('无法判断')) {
        if (item.claim.includes('场景判断')) {
          texts.push(item.claim.replace('场景判断：', ''))
        } else {
          texts.push(item.claim)
        }
      }
    })
    
    // 从房间分析提取标签
    const room = analysis.room_analysis || {}
    if (room.clues) {
      if (room.clues.space_layout && !room.clues.space_layout.includes('未见')) {
        tags.push({ icon: '🏠', text: room.clues.space_layout.substring(0, 8) })
      }
      if (room.clues.decoration && !room.clues.decoration.includes('未见')) {
        tags.push({ icon: '🎨', text: room.clues.decoration.substring(0, 8) })
      }
    }
    
    const person = analysis.person || {}
    if (person.gender && person.gender !== '无法判断') {
      tags.push({ icon: '👤', text: person.gender })
    }
    
    return {
      text: texts.length > 0 ? texts.join('。') : '未能识别明确的生活方式特征',
      tags: tags.slice(0, 4)
    }
  }

  // 收集细节发现
  const getDetailFindings = (analysis) => {
    if (!analysis) return { quote: '', items: [] }
    
    const items = []
    
    // 房间描述作为引用
    const room = analysis.room_analysis || {}
    let quote = ''
    if (room.evidence && room.evidence.length > 0) {
      quote = room.evidence.find(e => e.includes('来自') || e.length > 20) || room.evidence[0]
    }
    
    // 从各模块收集细节
    const detailItems = analysis.details?.items || []
    detailItems.forEach(item => {
      if (item.claim && !item.claim.includes('无法') && !item.claim.includes('暂不可用')) {
        items.push({ icon: '📝', text: item.claim })
      }
    })
    
    // 房间线索
    if (room.clues) {
      Object.entries(room.clues).forEach(([key, value]) => {
        if (value && !value.includes('未见相关')) {
          const icons = {
            tableware: '🍽️',
            seating: '🪑',
            personal_items: '🎒',
            decoration: '🖼️',
            space_layout: '📐'
          }
          items.push({ icon: icons[key] || '📌', text: value })
        }
      })
    }
    
    // 人物特征
    const person = analysis.person || {}
    if (person.evidence_list) {
      person.evidence_list.forEach(e => {
        if (e && !e.includes('N/A')) {
          items.push({ icon: '👁️', text: e })
        }
      })
    }
    
    return { quote: quote || '正在分析照片中的细节信息...', items: items.slice(0, 6) }
  }

  const analysis = result?.analysis
  const reliability = calculateReliability(analysis)
  const lifestyle = getLifestyleSummary(analysis)
  const details = getDetailFindings(analysis)

  return (
    <div className="app">
      {/* 顶部导航栏 */}
      <nav className="navbar">
        <div className="navbar-left">
          <div className="logo-icon">
            <img src="/logo.png" alt="网恋安全卫士" />
          </div>
          <div className="logo-text">
            <span className="logo-title">网恋安全卫士</span>
            <div className="logo-subtitle">
              <span className="beta-tag">BETA</span>
              <span className="slogan">HO DO YO DO</span>
            </div>
          </div>
        </div>
        <div className="status-indicator">
          <div className={`status-dot ${loading ? 'loading' : result ? 'done' : ''}`}></div>
          <span className="status-text">
            {loading ? 'Loadin...' : result ? 'Done' : 'Hello'}
          </span>
        </div>
      </nav>

      {/* 主内容区 */}
      <div className="main-content">
        {/* 左侧上传区域 */}
        <div className="upload-column">
          {/* 分析对象选择 */}
          <div className="window-card gender-select-card">
            <div className="window-header">
              <div className="window-header-left">
                <span className="window-header-icon">🔍</span>
                <span>SELECT_TARGET.exe</span>
              </div>
            </div>
            <div className="gender-select-content">
              <button 
                className={`gender-btn ${targetGender === 'boyfriend' ? 'active' : ''}`}
                onClick={() => setTargetGender('boyfriend')}
              >
                <span className="gender-icon">👦</span>
                <span className="gender-label">男朋友</span>
              </button>
              <button 
                className={`gender-btn ${targetGender === 'girlfriend' ? 'active' : ''}`}
                onClick={() => setTargetGender('girlfriend')}
              >
                <span className="gender-icon">👧</span>
                <span className="gender-label">女朋友</span>
              </button>
            </div>
          </div>

          <div className="window-card upload-card">
            <div className="window-header">
              <div className="window-header-left">
                <span className="window-header-icon">💜</span>
                <span>INPUT: JPG</span>
              </div>
              <div className="window-controls">
                <button className="window-btn-text">DRAG & DROP</button>
              </div>
            </div>
            <div className="upload-content">
              <div 
                className={`upload-area ${dragging ? 'dragging' : ''}`}
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onClick={() => document.getElementById('fileInput').click()}
              >
                {preview ? (
                  <div className="preview-container">
                    <img src={preview} alt="预览" className="preview-image" />
                  </div>
                ) : (
                  <>
                    <div className="upload-icon-box">
                      <span className="upload-icon">⬆️</span>
                    </div>
                    <div className="upload-text">DRAG DROP</div>
                    <div className="upload-text-sub">PHOTO</div>
                  </>
                )}
                <input 
                  type="file" 
                  id="fileInput"
                  accept="image/jpeg,image/png,image/webp"
                  style={{ display: 'none' }}
                  onChange={handleInputChange}
                />
              </div>
              <div className="upload-actions" style={{ marginTop: '16px' }}>
                <button 
                  className="btn-select"
                  onClick={() => document.getElementById('fileInput').click()}
                >
                  SELECT FILE
                </button>
                <span className="format-hint">SUPPORT: JPG, PNG, WEBP</span>
              </div>
            </div>
            <div className="scan-section">
              <button 
                className="btn-scan" 
                onClick={analyzeImage}
                disabled={!selectedFile || loading || !targetGender}
              >
                <span>🔍</span>
                <span>{loading ? 'SCANNING...' : 'SCAN'}</span>
              </button>
            </div>
          </div>

          {/* Helper Bot 窗口 */}
          <div className="window-card helper-card">
            <div className="window-header">
              <div className="window-header-left">
                <span className="window-header-icon">&gt;_</span>
                <span>HELPER.BOT</span>
              </div>
              <div className="window-controls">
                <button className="window-btn">−</button>
                <button className="window-btn">□</button>
                <button className="window-btn">×</button>
              </div>
            </div>
            <div className="helper-content">
              <div className="helper-avatar">🤖</div>
              <div className="helper-text">
                {!targetGender 
                  ? 'Step 1: Select target...' 
                  : !selectedFile 
                    ? 'Step 2: Upload photo...' 
                    : loading 
                      ? 'AI analyzing...' 
                      : result 
                        ? 'Done! Check results' 
                        : 'Step 3: Click SCAN'}
              </div>
            </div>
          </div>

          {error && <div className="error-message">❌ {error}</div>}
        </div>

        {/* 右侧结果区域 */}
        <div className="results-column">
          {loading ? (
            <div className="window-card">
              <div className="loading-overlay">
                <div className="loading-spinner"></div>
                <p className="loading-text">Analyzing photo, please wait...</p>
              </div>
            </div>
          ) : result && analysis ? (
            <>
              {/* 闺蜜吐槽卡片 - 最重要 */}
              {result.girlfriend_comments && result.girlfriend_comments.length > 0 && (
                <div className="window-card girlfriend-card">
                  <div className="window-header" onClick={() => toggleCollapse('girlfriend')} style={{ cursor: 'pointer' }}>
                    <div className="window-header-left">
                      <span className="window-header-icon">👁️</span>
                      <span>真相只有一个</span>
                    </div>
                    <div className="window-controls">
                      <button className="window-btn">{collapsed.girlfriend ? '▼' : '▲'}</button>
                    </div>
                  </div>
                  {!collapsed.girlfriend && (
                    <div className="girlfriend-content">
                      <div className="girlfriend-header">
                        <span className="girlfriend-avatar">💁‍♀️</span>
                        <span className="girlfriend-title">
                          朋友们帮你看了一眼{targetGender === 'boyfriend' ? '他' : '她'}发的照片...
                        </span>
                      </div>
                      <div className="girlfriend-comments">
                        {result.girlfriend_comments.map((comment, idx) => (
                          <div key={idx} className="girlfriend-comment">
                            <span className="comment-bullet">⚠️</span>
                            <span className="comment-text">{comment}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* 生活方式分析 */}
              <div className="window-card lifestyle-card">
                <div className="window-header" onClick={() => toggleCollapse('lifestyle')} style={{ cursor: 'pointer' }}>
                  <div className="window-header-left">
                    <span className="window-header-icon">🎯</span>
                    <span>生活方式分析</span>
                  </div>
                  <div className="window-controls">
                    <button className="window-btn">{collapsed.lifestyle ? '▼' : '▲'}</button>
                  </div>
                </div>
                {!collapsed.lifestyle && (
                  <div className="lifestyle-content">
                    <p className="analysis-text">{lifestyle.text}</p>
                    <div className="tags-container">
                      {lifestyle.tags.map((tag, idx) => (
                        <span key={idx} className="analysis-tag">
                          <span className="tag-icon">{tag.icon}</span>
                          {tag.text}
                        </span>
                      ))}
                      {analysis.room_analysis?.inferred_people_count && 
                       analysis.room_analysis.inferred_people_count !== '无法判断' && (
                        <span className="analysis-tag">
                          <span className="tag-icon">👥</span>
                          推断{analysis.room_analysis.inferred_people_count}人
                        </span>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* 人物体态分析 */}
              {analysis.person?.detected && (
                <div className="window-card body-card">
                  <div className="window-header" onClick={() => toggleCollapse('body')} style={{ cursor: 'pointer' }}>
                    <div className="window-header-left">
                      <span className="window-header-icon">🧑</span>
                      <span>人物体态分析</span>
                    </div>
                    <div className="window-controls">
                      <button className="window-btn">{collapsed.body ? '▼' : '▲'}</button>
                    </div>
                  </div>
                  {!collapsed.body && (
                    <div className="body-content">
                    <div className="body-stats">
                      <div className="body-stat">
                        <span className="stat-icon">📊</span>
                        <span className="stat-label">体型</span>
                        <span className="stat-value">{analysis.person.body_type}</span>
                      </div>
                      <div className="body-stat">
                        <span className="stat-icon">📏</span>
                        <span className="stat-label">身高</span>
                        <span className="stat-value">{analysis.person.height}</span>
                      </div>
                      <div className="body-stat">
                        <span className="stat-icon">🧘</span>
                        <span className="stat-label">姿态</span>
                        <span className="stat-value">{analysis.person.posture}</span>
                      </div>
                      <div className="body-stat">
                        <span className="stat-icon">👤</span>
                        <span className="stat-label">性别</span>
                        <span className="stat-value">{analysis.person.gender}</span>
                      </div>
                    </div>
                    {analysis.person.partial_features && (
                      <div className="partial-features">
                        <div className="features-title">🔍 局部特征分析</div>
                        <div className="features-grid">
                          {analysis.person.partial_features.hand && !analysis.person.partial_features.hand.includes('未见') && (
                            <div className="feature-item">
                              <span className="feature-icon">✋</span>
                              <span className="feature-text">{analysis.person.partial_features.hand}</span>
                            </div>
                          )}
                          {analysis.person.partial_features.arm && !analysis.person.partial_features.arm.includes('未见') && (
                            <div className="feature-item">
                              <span className="feature-icon">💪</span>
                              <span className="feature-text">{analysis.person.partial_features.arm}</span>
                            </div>
                          )}
                          {analysis.person.partial_features.face && !analysis.person.partial_features.face.includes('未见') && (
                            <div className="feature-item">
                              <span className="feature-icon">😊</span>
                              <span className="feature-text">{analysis.person.partial_features.face}</span>
                            </div>
                          )}
                          {analysis.person.partial_features.neck_shoulder && !analysis.person.partial_features.neck_shoulder.includes('未见') && (
                            <div className="feature-item">
                              <span className="feature-icon">🧑‍🤝‍🧑</span>
                              <span className="feature-text">{analysis.person.partial_features.neck_shoulder}</span>
                            </div>
                          )}
                        </div>
                        {analysis.person.partial_features.body_type_clue && (
                          <div className="body-clue">
                            <span className="clue-label">💡 体态综合判断：</span>
                            <span className="clue-text">{analysis.person.partial_features.body_type_clue}</span>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                  )}
                </div>
              )}

              {/* 隐藏细节发现 */}
              <div className="window-card details-card">
                <div className="window-header" onClick={() => toggleCollapse('details')} style={{ cursor: 'pointer' }}>
                  <div className="window-header-left">
                    <span className="window-header-icon">🔍</span>
                    <span>隐藏细节发现</span>
                  </div>
                  <div className="window-controls">
                    <button className="window-btn">{collapsed.details ? '▼' : '▲'}</button>
                  </div>
                </div>
                {!collapsed.details && (
                  <div className="details-content">
                    <div className="quote-text">"{details.quote}"</div>
                    <ul className="detail-list">
                      {details.items.map((item, idx) => (
                        <li key={idx} className="detail-item">
                          <span className="detail-bullet">◆</span>
                          <span className="detail-icon">{item.icon}</span>
                          <span>{item.text}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              {/* 可靠性评估 */}
              <div className="window-card reliability-card">
                <div className="window-header" onClick={() => toggleCollapse('reliability')} style={{ cursor: 'pointer' }}>
                  <div className="window-header-left">
                    <span className="window-header-icon">⚖️</span>
                    <span>可靠性评估</span>
                  </div>
                  <div className="window-controls">
                    <button className="window-btn">{collapsed.reliability ? '▼' : '▲'}</button>
                  </div>
                </div>
                {!collapsed.reliability && (
                  <div className="reliability-content">
                  <div className="reliability-badge-container">
                    <span className={`reliability-badge badge-${reliability.level}`}>
                      {reliability.label}
                    </span>
                  </div>
                  <p className="reliability-summary">{reliability.summary}</p>
                  <div className="confidence-list">
                    {analysis.credibility?.items?.slice(0, 3).map((item, idx) => (
                      <div key={idx} className="confidence-item">
                        <span className="conf-icon">
                          {item.confidence === 'high' ? '✅' : item.confidence === 'medium' ? '⚠️' : '❓'}
                        </span>
                        <span className="conf-text">{item.claim}</span>
                        <span className={`conf-tag conf-${item.confidence}`}>
                          {item.confidence === 'high' ? '高' : item.confidence === 'medium' ? '中' : '低'}
                        </span>
                      </div>
                    ))}
                  </div>
                  {analysis.room_analysis?.limitations && (
                    <div className="limitations-box">
                      <div className="limitations-title">⚠️ 分析局限性</div>
                      <ul className="limitations-list">
                        {analysis.room_analysis.limitations.slice(0, 2).map((lim, idx) => (
                          <li key={idx}>{lim}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="awaiting-card">
              <div className="awaiting-icon">📷</div>
              <div className="awaiting-title">AWAITING_DATA</div>
              <div className="awaiting-desc">
                Upload a photo to decrypt social clues,<br/>
                hidden metadata, and lifestyle indicators.
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default App
