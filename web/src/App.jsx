import { useState, useCallback } from 'react'

function App() {
  const [selectedFile, setSelectedFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [dragging, setDragging] = useState(false)
  const [targetGender, setTargetGender] = useState(null)
  
  // 折叠状态 - 新增更多模块
  const [collapsed, setCollapsed] = useState({
    girlfriend: false,
    webCheck: false,    // 新增：网图检测
    scene: false,       // 新增：场景分析
    lifestyle: false,
    body: false,
    objects: false,     // 新增：物品检测
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
      console.log('API Response:', data) // 调试用
      setResult(data)
    } catch (err) {
      setError(err.message || '网络错误，请重试')
    } finally {
      setLoading(false)
    }
  }

  // ==================== 辅助函数 ====================
  
  const 包含无效 = (str) => {
    if (!str) return true
    return str.includes('未见') || str.includes('无法') || str.includes('N/A') || str.includes('不可见') || str.includes('null')
  }

  // 获取网图检测风险等级样式
  const getWebCheckRiskClass = (level) => {
    if (level === 'high') return 'risk-high'
    if (level === 'medium') return 'risk-medium'
    return 'risk-low'
  }

  // 获取可靠性评估
  const calculateReliability = (analysis, girlfriendComments = []) => {
    if (!analysis) {
      return {
        level: 'unknown',
        label: '无法判断',
        summary: '暂无足够信息进行分析',
        suspiciousCount: 0
      }
    }
    
    let score = 100
    const suspiciousCount = girlfriendComments?.length || 0
    
    // 网图检测扣分
    const webCheck = analysis.web_image_check
    if (webCheck) {
      if (webCheck.risk_level === 'high') score -= 40
      else if (webCheck.risk_level === 'medium') score -= 20
      if (webCheck.watermark?.detected) score -= 15
      if (webCheck.screenshot_traces?.detected) score -= 10
      if (webCheck.professional_photo?.detected) score -= 10
    }
    
    // 可疑点扣分
    score -= Math.min(suspiciousCount * 10, 30)
    
    let level, label, summary
    if (score >= 75) {
      level = 'high'
      label = '照片可信度较高'
      summary = suspiciousCount === 0 
        ? '技术指标正常，未发现明显可疑点。'
        : `技术指标正常，但有${suspiciousCount}个小细节值得留意。`
    } else if (score >= 50) {
      level = 'medium'
      label = '可信度中等'
      summary = suspiciousCount >= 2
        ? `这照片有${suspiciousCount}个地方看着怎么那么奇怪？`
        : '有些指标不确定，建议结合其他照片综合判断。'
    } else {
      level = 'low'
      label = '可信度较低'
      summary = '多项指标存在疑问，这照片真实性得打个问号...'
    }
    
    return { level, label, summary, suspiciousCount, score }
  }

  // 获取分析数据 - 兼容多种后端返回格式
  const getAnalysisData = () => {
    if (!result) return null
    
    // 尝试多种可能的数据路径
    const analysis = result.analysis || result.qwen || result
    const girlfriendComments = result.girlfriend_comments || analysis?.girlfriend_comments || []
    
    return {
      analysis,
      girlfriendComments,
      // 各模块数据
      person: analysis?.person,
      webCheck: analysis?.web_image_check,
      scene: analysis?.scene,
      lifestyle: analysis?.lifestyle,
      roomAnalysis: analysis?.room_analysis,
      objects: analysis?.objects,
      intention: analysis?.intention,
      details: analysis?.details
    }
  }

  const data = getAnalysisData()
  const reliability = data ? calculateReliability(data.analysis, data.girlfriendComments) : null

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
            {loading ? 'Loading...' : result ? 'Done' : 'Hello'}
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
                        ? 'Done! Check results →' 
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
          ) : data && data.analysis ? (
            <>
              {/* ========== 1. 网图检测警告（最重要，放最前面） ========== */}
              {data.webCheck && (data.webCheck.risk_level === 'high' || data.webCheck.risk_level === 'medium') && (
                <div className={`window-card webcheck-card ${getWebCheckRiskClass(data.webCheck.risk_level)}`}>
                  <div className="window-header" onClick={() => toggleCollapse('webCheck')} style={{ cursor: 'pointer' }}>
                    <div className="window-header-left">
                      <span className="window-header-icon">⚠️</span>
                      <span>网图检测预警</span>
                      <span className={`risk-badge ${getWebCheckRiskClass(data.webCheck.risk_level)}`}>
                        {data.webCheck.risk_level === 'high' ? '高风险' : '中风险'}
                      </span>
                    </div>
                    <div className="window-controls">
                      <button className="window-btn">{collapsed.webCheck ? '▼' : '▲'}</button>
                    </div>
                  </div>
                  {!collapsed.webCheck && (
                    <div className="webcheck-content">
                      <div className="webcheck-summary">
                        {data.webCheck.conclusion || '检测到网图可疑特征'}
                      </div>
                      
                      <div className="webcheck-grid">
                        {/* 水印检测 */}
                        {data.webCheck.watermark?.detected && (
                          <div className="webcheck-item detected">
                            <span className="item-icon">🏷️</span>
                            <span className="item-label">水印检测</span>
                            <span className="item-value">
                              {data.webCheck.watermark.platform || '检测到水印'}
                              {data.webCheck.watermark.location && ` (${data.webCheck.watermark.location})`}
                            </span>
                          </div>
                        )}
                        
                        {/* 截图痕迹 */}
                        {data.webCheck.screenshot_traces?.detected && (
                          <div className="webcheck-item detected">
                            <span className="item-icon">📱</span>
                            <span className="item-label">截图痕迹</span>
                            <span className="item-value">{data.webCheck.screenshot_traces.type || '检测到截图'}</span>
                          </div>
                        )}
                        
                        {/* 专业摄影 */}
                        {data.webCheck.professional_photo?.detected && (
                          <div className="webcheck-item detected">
                            <span className="item-icon">📸</span>
                            <span className="item-label">专业摄影</span>
                            <span className="item-value">
                              {data.webCheck.professional_photo.features?.join('、') || '专业拍摄特征'}
                            </span>
                          </div>
                        )}
                        
                        {/* 网红风格 */}
                        {data.webCheck.influencer_style?.detected && (
                          <div className="webcheck-item detected">
                            <span className="item-icon">💄</span>
                            <span className="item-label">网红风格</span>
                            <span className="item-value">
                              {data.webCheck.influencer_style.features?.join('、') || '网红特征'}
                            </span>
                          </div>
                        )}
                        
                        {/* 图片质量问题 */}
                        {(data.webCheck.image_quality_issues?.compression_artifacts || 
                          data.webCheck.image_quality_issues?.resolution_mismatch) && (
                          <div className="webcheck-item detected">
                            <span className="item-icon">🖼️</span>
                            <span className="item-label">质量异常</span>
                            <span className="item-value">{data.webCheck.image_quality_issues.evidence || '图片质量异常'}</span>
                          </div>
                        )}
                        
                        {/* 时间矛盾 */}
                        {data.webCheck.temporal_inconsistency?.detected && (
                          <div className="webcheck-item detected">
                            <span className="item-icon">⏰</span>
                            <span className="item-label">时间矛盾</span>
                            <span className="item-value">{data.webCheck.temporal_inconsistency.evidence}</span>
                          </div>
                        )}
                      </div>
                      
                      {data.webCheck.recommendation && (
                        <div className="webcheck-recommendation">
                          💡 {data.webCheck.recommendation}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* ========== 2. 闺蜜吐槽卡片 ========== */}
              {data.girlfriendComments && data.girlfriendComments.length > 0 && (
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
                        {data.girlfriendComments.map((comment, idx) => (
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

              {/* ========== 3. 场景分析 ========== */}
              {data.scene && (
                <div className="window-card scene-card">
                  <div className="window-header" onClick={() => toggleCollapse('scene')} style={{ cursor: 'pointer' }}>
                    <div className="window-header-left">
                      <span className="window-header-icon">📍</span>
                      <span>场景分析</span>
                    </div>
                    <div className="window-controls">
                      <button className="window-btn">{collapsed.scene ? '▼' : '▲'}</button>
                    </div>
                  </div>
                  {!collapsed.scene && (
                    <div className="scene-content">
                      <div className="scene-main">
                        <span className="scene-type-badge">
                          {data.scene.location_type === '室内' ? '🏠 室内' : 
                           data.scene.location_type === '室外' ? '🌳 室外' : '❓ 未知'}
                        </span>
                        <span className="scene-env">{data.scene.environment || '环境信息待分析'}</span>
                      </div>
                      {data.scene.evidence?.length > 0 && (
                        <div className="scene-evidence">
                          {data.scene.evidence.map((e, idx) => (
                            <div key={idx} className="evidence-item">◆ {e}</div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* ========== 4. 生活方式分析 ========== */}
              {data.lifestyle && (
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
                      {data.lifestyle.claim && (
                        <p className="analysis-text">{data.lifestyle.claim}</p>
                      )}
                      
                      <div className="lifestyle-stats">
                        {data.lifestyle.consumption_level && data.lifestyle.consumption_level !== '无法判断' && (
                          <div className="lifestyle-stat">
                            <span className="stat-icon">💰</span>
                            <span className="stat-label">消费水平</span>
                            <span className="stat-value">{data.lifestyle.consumption_level}</span>
                          </div>
                        )}
                        {data.lifestyle.accommodation_level && data.lifestyle.accommodation_level !== '无法判断' && (
                          <div className="lifestyle-stat">
                            <span className="stat-icon">🏨</span>
                            <span className="stat-label">住宿档次</span>
                            <span className="stat-value">{data.lifestyle.accommodation_level}</span>
                          </div>
                        )}
                      </div>
                      
                      {/* 品牌识别 - 兼容 brands_detected 和 brands_info */}
                      {(data.lifestyle.brands_detected || data.lifestyle.brands_info) && (
                        <div className="brands-section">
                          <div className="brands-header">
                            <span className="brands-icon">🏷️</span>
                            <span className="brands-title">识别到的品牌</span>
                          </div>
                          <div className="brands-grid">
                            {Object.entries(data.lifestyle.brands_detected || {}).map(([category, brands]) => 
                              brands?.length > 0 && brands[0] !== '' && (
                                <div key={category} className="brand-category">
                                  <span className="category-label">
                                    {category === 'clothing' ? '👔 服装' :
                                     category === 'accessories' ? '👜 配饰' :
                                     category === 'electronics' ? '📱 电子' :
                                     category === 'skincare' ? '🧴 护肤' : '📦 其他'}
                                  </span>
                                  <div className="brand-tags">
                                    {brands.filter(b => b).map((brand, i) => (
                                      <span key={i} className="brand-tag">{brand}</span>
                                    ))}
                                  </div>
                                </div>
                              )
                            )}
                          </div>
                        </div>
                      )}
                      
                      {data.lifestyle.evidence?.length > 0 && (
                        <div className="lifestyle-evidence">
                          {data.lifestyle.evidence.map((e, idx) => (
                            <div key={idx} className="evidence-item">◆ {e}</div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* ========== 5. 人物体态分析 ========== */}
              {data.person?.detected && (
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
                          <span className="stat-icon">👤</span>
                          <span className="stat-label">性别</span>
                          <span className="stat-value">{data.person.gender || '无法判断'}</span>
                        </div>
                        <div className="body-stat">
                          <span className="stat-icon">📏</span>
                          <span className="stat-label">身高</span>
                          <span className="stat-value">{data.person.height || '无法判断'}</span>
                        </div>
                        <div className="body-stat">
                          <span className="stat-icon">📊</span>
                          <span className="stat-label">体型</span>
                          <span className="stat-value">{data.person.body_type || '无法判断'}</span>
                        </div>
                        <div className="body-stat">
                          <span className="stat-icon">🧘</span>
                          <span className="stat-label">姿态</span>
                          <span className="stat-value">{data.person.posture || '不确定'}</span>
                        </div>
                      </div>
                      
                      {/* 性别判断依据 */}
                      {data.person.gender_evidence && (
                        <div className="gender-evidence">
                          <div className="evidence-title">🔍 性别判断依据</div>
                          {data.person.gender_evidence.appearance && !包含无效(data.person.gender_evidence.appearance) && (
                            <div className="evidence-row">
                              <span className="evidence-label">外观线索:</span>
                              <span className="evidence-text">{data.person.gender_evidence.appearance}</span>
                            </div>
                          )}
                          {data.person.gender_evidence.environment && !包含无效(data.person.gender_evidence.environment) && (
                            <div className="evidence-row">
                              <span className="evidence-label">环境线索:</span>
                              <span className="evidence-text">{data.person.gender_evidence.environment}</span>
                            </div>
                          )}
                        </div>
                      )}
                      
                      {/* 局部特征 */}
                      {data.person.partial_features && (
                        <div className="partial-features">
                          <div className="features-title">🔍 局部特征分析</div>
                          <div className="features-grid">
                            {data.person.partial_features.hand && !包含无效(data.person.partial_features.hand) && (
                              <div className="feature-item">
                                <span className="feature-icon">✋</span>
                                <span className="feature-text">{data.person.partial_features.hand}</span>
                              </div>
                            )}
                            {data.person.partial_features.arm && !包含无效(data.person.partial_features.arm) && (
                              <div className="feature-item">
                                <span className="feature-icon">💪</span>
                                <span className="feature-text">{data.person.partial_features.arm}</span>
                              </div>
                            )}
                            {data.person.partial_features.body && !包含无效(data.person.partial_features.body) && (
                              <div className="feature-item">
                                <span className="feature-icon">🧍</span>
                                <span className="feature-text">{data.person.partial_features.body}</span>
                              </div>
                            )}
                            {data.person.partial_features.face && !包含无效(data.person.partial_features.face) && (
                              <div className="feature-item">
                                <span className="feature-icon">😊</span>
                                <span className="feature-text">{data.person.partial_features.face}</span>
                              </div>
                            )}
                            {data.person.partial_features.neck_shoulder && !包含无效(data.person.partial_features.neck_shoulder) && (
                              <div className="feature-item">
                                <span className="feature-icon">🧣</span>
                                <span className="feature-text">{data.person.partial_features.neck_shoulder}</span>
                              </div>
                            )}
                          </div>
                          {data.person.partial_features.body_type_clue && (
                            <div className="body-clue">
                              <span className="clue-label">💡 体态综合判断：</span>
                              <span className="clue-text">{data.person.partial_features.body_type_clue}</span>
                            </div>
                          )}
                        </div>
                      )}
                      
                      {/* 体征证据 */}
                      {data.person.evidence && (
                        <div className="person-evidence">
                          <div className="evidence-title">📐 判断依据</div>
                          <div className="evidence-grid">
                            {data.person.evidence.reference && (
                              <div className="evidence-item">
                                <span className="label">参照物:</span>
                                <span className="value">{data.person.evidence.reference}</span>
                              </div>
                            )}
                            {data.person.evidence.body_visibility && (
                              <div className="evidence-item">
                                <span className="label">可见范围:</span>
                                <span className="value">{data.person.evidence.body_visibility}</span>
                              </div>
                            )}
                            {data.person.evidence.angle_impact && (
                              <div className="evidence-item">
                                <span className="label">角度影响:</span>
                                <span className="value">{data.person.evidence.angle_impact}</span>
                              </div>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* ========== 6. 物品检测 ========== */}
              {data.objects?.detected?.length > 0 && (
                <div className="window-card objects-card">
                  <div className="window-header" onClick={() => toggleCollapse('objects')} style={{ cursor: 'pointer' }}>
                    <div className="window-header-left">
                      <span className="window-header-icon">📦</span>
                      <span>物品检测</span>
                    </div>
                    <div className="window-controls">
                      <button className="window-btn">{collapsed.objects ? '▼' : '▲'}</button>
                    </div>
                  </div>
                  {!collapsed.objects && (
                    <div className="objects-content">
                      <div className="objects-list">
                        {data.objects.detected.map((obj, idx) => (
                          <span key={idx} className="object-tag">{obj}</span>
                        ))}
                      </div>
                      {data.objects.brands?.length > 0 && data.objects.brands[0] && (
                        <div className="objects-brands">
                          <span className="brands-label">识别品牌:</span>
                          {data.objects.brands.filter(b => b).map((brand, idx) => (
                            <span key={idx} className="brand-tag highlight">{brand}</span>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* ========== 7. 房间/环境分析 ========== */}
              {data.roomAnalysis && data.scene?.location_type === '室内' && (
                <div className="window-card room-card">
                  <div className="window-header">
                    <div className="window-header-left">
                      <span className="window-header-icon">🏠</span>
                      <span>房间环境分析</span>
                    </div>
                  </div>
                  <div className="room-content">
                    <div className="room-summary">
                      <div className="room-stat">
                        <span className="stat-label">推断人数</span>
                        <span className="stat-value">{data.roomAnalysis.inferred_people_count || '无法判断'}</span>
                      </div>
                      <div className="room-stat">
                        <span className="stat-label">关系推断</span>
                        <span className="stat-value">{data.roomAnalysis.relationship_hint || '无法判断'}</span>
                      </div>
                    </div>
                    
                    {data.roomAnalysis.clues && (
                      <div className="room-clues">
                        <div className="clues-title">🔍 环境线索</div>
                        <div className="clues-grid">
                          {Object.entries(data.roomAnalysis.clues).map(([key, value]) => 
                            value && !包含无效(value) && (
                              <div key={key} className="clue-item">
                                <span className="clue-icon">
                                  {key === 'tableware' ? '🍽️' :
                                   key === 'seating' ? '🪑' :
                                   key === 'personal_items' ? '🎒' :
                                   key === 'decoration' ? '🖼️' :
                                   key === 'space_layout' ? '📐' : '📌'}
                                </span>
                                <span className="clue-text">{value}</span>
                              </div>
                            )
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* ========== 8. 文字与细节检测 ========== */}
              {data.details && (
                <div className="window-card details-card">
                  <div className="window-header" onClick={() => toggleCollapse('details')} style={{ cursor: 'pointer' }}>
                    <div className="window-header-left">
                      <span className="window-header-icon">📝</span>
                      <span>文字与细节检测</span>
                    </div>
                    <div className="window-controls">
                      <button className="window-btn">{collapsed.details ? '▼' : '▲'}</button>
                    </div>
                  </div>
                  {!collapsed.details && (
                    <div className="details-content">
                      {/* 文字检测 */}
                      {data.details.text_detected?.length > 0 && (
                        <div className="text-detection">
                          <div className="detection-title">📖 识别到的文字</div>
                          <div className="text-type">
                            类型: {data.details.text_type || '未知'} 
                            {data.details.text_source && ` | 来源: ${data.details.text_source}`}
                          </div>
                          <div className="text-list">
                            {data.details.text_detected.map((text, idx) => (
                              <span key={idx} className="text-tag">"{text}"</span>
                            ))}
                          </div>
                        </div>
                      )}
                      
                      {/* 特殊元素 */}
                      {data.details.special_elements?.length > 0 && (
                        <div className="special-elements">
                          <div className="detection-title">✨ 特殊元素</div>
                          <div className="elements-list">
                            {data.details.special_elements.map((elem, idx) => (
                              <span key={idx} className="element-tag">{elem}</span>
                            ))}
                          </div>
                        </div>
                      )}
                      
                      {/* 证据 */}
                      {data.details.evidence?.length > 0 && (
                        <div className="details-evidence">
                          {data.details.evidence.map((e, idx) => (
                            <div key={idx} className="evidence-item">◆ {e}</div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* ========== 9. 拍摄意图分析 ========== */}
              {data.intention?.claim && data.intention.claim !== '无法判断' && (
                <div className="window-card intention-card">
                  <div className="window-header">
                    <div className="window-header-left">
                      <span className="window-header-icon">🎯</span>
                      <span>拍摄意图分析</span>
                    </div>
                  </div>
                  <div className="intention-content">
                    <div className="intention-claim">{data.intention.claim}</div>
                    {data.intention.evidence?.length > 0 && (
                      <div className="intention-evidence">
                        {data.intention.evidence.map((e, idx) => (
                          <div key={idx} className="evidence-item">◆ {e}</div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* ========== 10. 可靠性评估 ========== */}
              <div className="window-card reliability-card">
                <div className="window-header" onClick={() => toggleCollapse('reliability')} style={{ cursor: 'pointer' }}>
                  <div className="window-header-left">
                    <span className="window-header-icon">⚖️</span>
                    <span>综合可靠性评估</span>
                  </div>
                  <div className="window-controls">
                    <button className="window-btn">{collapsed.reliability ? '▼' : '▲'}</button>
                  </div>
                </div>
                {!collapsed.reliability && reliability && (
                  <div className="reliability-content">
                    <div className="reliability-badge-container">
                      <span className={`reliability-badge badge-${reliability.level}`}>
                        {reliability.label}
                      </span>
                      <span className="reliability-score">{reliability.score}分</span>
                    </div>
                    <p className="reliability-summary">{reliability.summary}</p>
                    
                    {/* 网图检测摘要 */}
                    {data.webCheck && (
                      <div className="webcheck-summary-mini">
                        <span className="summary-icon">
                          {data.webCheck.is_likely_web_image ? '⚠️' : '✅'}
                        </span>
                        <span className="summary-text">
                          网图风险: {data.webCheck.risk_level === 'high' ? '高' : 
                                    data.webCheck.risk_level === 'medium' ? '中' : '低'}
                        </span>
                      </div>
                    )}
                    
                    {/* 局限性说明 */}
                    {data.roomAnalysis?.limitations?.length > 0 && (
                      <div className="limitations-box">
                        <div className="limitations-title">⚠️ 分析局限性</div>
                        <ul className="limitations-list">
                          {data.roomAnalysis.limitations.map((lim, idx) => (
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
