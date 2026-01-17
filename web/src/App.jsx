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

  // ==================== 新架构：三维度可靠性分析 ====================
  
  /**
   * 计算可靠性门控系数 (Reliability Gating)
   * 返回各维度的可靠性系数 r ∈ [0, 1]
   */
  const calculateReliabilityGates = (analysis) => {
    const gates = {
      exif: 0.5,      // EXIF可靠性
      clarity: 1.0,   // 清晰度
      angle: 1.0,     // 角度可靠性
      isOriginal: false  // 是否原图
    }
    
    if (!analysis) return gates
    
    // === EXIF两段式判断 ===
    const credibility = analysis.credibility || {}
    const exifItems = credibility.items?.filter(item => 
      item.claim?.includes('EXIF') || item.claim?.includes('元数据') || item.claim?.includes('相机')
    ) || []
    
    // 判断是否为原图（有EXIF且一致性高）
    const hasValidExif = exifItems.some(item => item.confidence === 'high')
    const hasExifWarning = exifItems.some(item => 
      item.claim?.includes('缺失') || item.claim?.includes('异常') || item.claim?.includes('修改')
    )
    
    if (hasValidExif && !hasExifWarning) {
      // 原图可能性高：EXIF权重=1
      gates.exif = 1.0
      gates.isOriginal = true
    } else if (hasExifWarning) {
      // 有明确的EXIF异常
      gates.exif = 0.3
    } else {
      // 截图/社交压缩：EXIF权重=0（中性，不扣分）
      gates.exif = 0  // 不参与计算
      gates.isOriginal = false
    }
    
    // === 清晰度/模糊度门控 ===
    const details = analysis.details || {}
    const isBlurry = details.items?.some(item => 
      item.claim?.includes('模糊') || item.claim?.includes('不清晰')
    )
    if (isBlurry) {
      gates.clarity = 0.5  // 模糊图片降低细节判断能力
    }
    
    // === 角度门控 ===
    const person = analysis.person || {}
    const angleImpact = person.evidence?.angle_impact || ''
    if (angleImpact.includes('影响大')) {
      gates.angle = 0.6
    } else if (angleImpact.includes('影响小')) {
      gates.angle = 1.0
    } else {
      gates.angle = 0.8  // 默认中等
    }
    
    return gates
  }
  
  /**
   * A. 技术真实性分 (Auth-Tech)
   * 编辑痕迹/AI生成/反搜网图/EXIF一致性
   */
  const calculateAuthTech = (analysis, gates) => {
    let score = 100  // 满分100，扣分制
    let findings = []
    let hasEvidence = false
    
    const credibility = analysis?.credibility || {}
    const items = credibility.items || []
    
    items.forEach(item => {
      const claim = item.claim || ''
      const conf = item.confidence
      
      // 编辑痕迹检测
      if (claim.includes('编辑') || claim.includes('PS') || claim.includes('修改')) {
        hasEvidence = true
        if (conf === 'high') {
          score -= 40
          findings.push('发现明显编辑痕迹')
        } else if (conf === 'medium') {
          score -= 20
          findings.push('可能存在编辑')
        }
      }
      
      // AI生成检测
      if (claim.includes('AI') || claim.includes('生成') || claim.includes('合成')) {
        hasEvidence = true
        if (conf === 'high') {
          score -= 50
          findings.push('疑似AI生成图片')
        } else if (conf === 'medium') {
          score -= 25
          findings.push('AI生成可能性中等')
        }
      }
      
      // EXIF一致性（仅在原图时考虑）
      if (gates.isOriginal && (claim.includes('EXIF') || claim.includes('元数据'))) {
        hasEvidence = true
        if (claim.includes('缺失') || claim.includes('异常')) {
          score -= 15 * gates.exif
          findings.push('EXIF信息异常')
        } else if (conf === 'high') {
          score += 5  // EXIF正常可以微加分
        }
      }
    })
    
    // 如果没有任何证据，给中等分
    if (!hasEvidence) {
      score = 70
      findings.push('未发现明显技术编辑痕迹')
    }
    
    return {
      score: Math.max(0, Math.min(100, score)),
      findings,
      label: score >= 80 ? '原片可能性高' : score >= 50 ? '有待进一步确认' : '存在编辑风险'
    }
  }
  
  /**
   * B. 语境一致性分 (Auth-Context)
   * 环境线索、反光/镜像、物理一致性、与叙述匹配
   */
  const calculateAuthContext = (analysis, girlfriendComments = []) => {
    let score = 100
    let findings = []
    let suspiciousItems = []
    
    // === 环境线索一致性 ===
    const room = analysis?.room_analysis || {}
    if (room.confidence === 'high') {
      score += 5
    } else if (room.confidence === 'low') {
      score -= 10
    }
    
    // === 可疑点分析（将girlfriendComments作为语境异常） ===
    const suspiciousCount = girlfriendComments?.length || 0
    if (suspiciousCount > 0) {
      // 每个可疑点扣分
      const penalty = Math.min(suspiciousCount * 15, 45)
      score -= penalty
      suspiciousItems = girlfriendComments.slice(0, 3)
      
      if (suspiciousCount >= 3) {
        findings.push(`发现${suspiciousCount}个可疑细节，有姐妹吗能抽空确认下？`)
      } else if (suspiciousCount >= 2) {
        findings.push(`有${suspiciousCount}个地方看着不对劲啊...`)
      } else {
        findings.push('有一个小细节需要留意')
      }
    } else {
      findings.push('暂未发现明显语境异常')
    }
    
    // === 物理一致性（光影/透视） ===
    const details = analysis?.details || {}
    const specialElements = details.items?.filter(item => 
      item.claim?.includes('反光') || item.claim?.includes('镜像') || item.claim?.includes('光影')
    ) || []
    
    if (specialElements.length > 0) {
      findings.push('画面中存在反光/镜像细节')
    }
    
    return {
      score: Math.max(0, Math.min(100, score)),
      findings,
      suspiciousItems,
      suspiciousCount,
      label: score >= 80 ? '语境一致' : score >= 50 ? '存在疑点' : '多处异常'
    }
  }
  
  /**
   * C. 画像置信度 (Profile-Confidence)
   * 不是“画像结论好坏”，而是“能否可靠推断”
   * 决定输出粒度（标签数量、语气强弱）
   */
  const calculateProfileConfidence = (analysis, gates) => {
    let score = 0
    let maxScore = 0
    let findings = []
    let outputGranularity = 'full'  // full/partial/minimal
    
    const person = analysis?.person || {}
    const lifestyle = analysis?.lifestyle || {}
    
    // === 人物可见性 ===
    maxScore += 30
    if (person.detected) {
      const bodyVis = person.evidence?.body_visibility || ''
      if (bodyVis.includes('全身')) {
        score += 30 * gates.angle
      } else if (bodyVis.includes('上半身')) {
        score += 20 * gates.angle
      } else if (bodyVis.includes('头肩')) {
        score += 10 * gates.angle
      } else {
        score += 5
      }
    }
    
    // === 参照物有效性 ===
    maxScore += 20
    const reference = person.evidence?.reference || ''
    if (reference && !reference.includes('无明显') && !reference.includes('N/A')) {
      score += 20 * gates.clarity
      findings.push('有有效参照物')
    }
    
    // === 局部特征丰富度 ===
    maxScore += 30
    const partialFeatures = person.partial_features || {}
    let featureCount = 0
    Object.values(partialFeatures).forEach(v => {
      if (v && !包含无效(v)) featureCount++
    })
    score += Math.min(featureCount * 6, 30) * gates.clarity
    
    // === 生活方式线索 ===
    maxScore += 20
    if (lifestyle.consumption_level && lifestyle.consumption_level !== '无法判断') {
      score += 10
    }
    if (lifestyle.accommodation_level && lifestyle.accommodation_level !== '无法判断') {
      score += 10
    }
    
    // 计算最终分数（归一化到100）
    const finalScore = maxScore > 0 ? (score / maxScore) * 100 : 50
    
    // 决定输出粒度
    if (finalScore >= 70) {
      outputGranularity = 'full'
      findings.push('画面质量足以支撑详细推断')
    } else if (finalScore >= 40) {
      outputGranularity = 'partial'
      findings.push('部分特征可推断，结论谨慎')
    } else {
      outputGranularity = 'minimal'
      findings.push('线索不足，建议追拍更清晰的照片')
    }
    
    // === 模糊度触发追拍建议 ===
    let needMorePhotos = false
    let morePhotosSuggestions = []
    
    if (gates.clarity < 0.8) {
      needMorePhotos = true
      morePhotosSuggestions.push('补一张更清晰的照片')
    }
    if (gates.angle < 0.8) {
      needMorePhotos = true
      morePhotosSuggestions.push('补一张不同角度的照片')
    }
    if (!reference || reference.includes('无明显')) {
      needMorePhotos = true
      morePhotosSuggestions.push('补一张带参照物的照片')
    }
    
    return {
      score: Math.round(finalScore),
      findings,
      outputGranularity,
      needMorePhotos,
      morePhotosSuggestions,
      label: finalScore >= 70 ? '可信赖推断' : finalScore >= 40 ? '部分可推断' : '线索不足'
    }
  }
  
  // 辅助函数：检查是否为无效值
  const 包含无效 = (str) => {
    if (!str) return true
    return str.includes('未见') || str.includes('无法') || str.includes('N/A') || str.includes('不可见')
  }
  
  /**
   * 综合可靠性评估（新架构入口）
   * 拆分为3个子分数，各司其责
   */
  const calculateReliability = (analysis, girlfriendComments = []) => {
    if (!analysis) {
      return {
        level: 'unknown',
        label: '无法判断',
        summary: '暂无足够信息进行分析',
        authTech: null,
        authContext: null,
        profileConf: null,
        suspiciousCount: 0
      }
    }
    
    // 1. 计算可靠性门控
    const gates = calculateReliabilityGates(analysis)
    
    // 2. 计算三个子分数
    const authTech = calculateAuthTech(analysis, gates)
    const authContext = calculateAuthContext(analysis, girlfriendComments)
    const profileConf = calculateProfileConfidence(analysis, gates)
    
    // 3. 综合评估（注意：profileConf不参与真伪判断，只作为粒度控制）
    // 真伪判断只看 Auth-Tech 和 Auth-Context
    const authScore = (authTech.score * 0.5 + authContext.score * 0.5)
    
    let level, label, summary
    const suspiciousCount = authContext.suspiciousCount
    
    if (authScore >= 75) {
      level = 'high'
      label = '照片可信度较高'
      if (suspiciousCount === 0) {
        summary = '技术指标正常，未发现明显可疑点。'
      } else {
        summary = `技术指标正常，但有${suspiciousCount}个小细节值得留意。`
      }
    } else if (authScore >= 50) {
      level = 'medium'
      label = '可信度中等'
      if (suspiciousCount >= 2) {
        summary = `哎呀姐妹，这照片有${suspiciousCount}个地方看着怎么那么奇怪？`
      } else if (suspiciousCount === 1) {
        summary = '基本正常，但有一个地方有点说不上来的微妙...'
      } else {
        summary = '有些指标不确定，建议结合其他照片综合判断。'
      }
    } else {
      level = 'low'
      label = '可信度较低'
      if (suspiciousCount >= 3) {
        summary = `我靠，这照片${suspiciousCount}个可疑点啊！哪个姐妹能帮我删了这人？`
      } else {
        summary = '多项指标存在疑问，这照片真实性得打个问号...'  
      }
    }
    
    // 追拍建议（来自 Profile-Confidence）
    if (profileConf.needMorePhotos && profileConf.morePhotosSuggestions.length > 0) {
      summary += '\n\n📸 追拍建议：' + profileConf.morePhotosSuggestions.join('、')
    }
    
    return {
      level,
      label,
      summary,
      // 三个子分数
      authTech,
      authContext, 
      profileConf,
      suspiciousCount,
      // 门控信息
      gates
    }
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
  const girlfriendComments = result?.girlfriend_comments || []
  const reliability = calculateReliability(analysis, girlfriendComments)
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
                    <span>图片元素分析</span>
                  </div>
                  <div className="window-controls">
                    <button className="window-btn">{collapsed.lifestyle ? '▼' : '▲'}</button>
                  </div>
                </div>
                {!collapsed.lifestyle && (
                  <div className="lifestyle-content">
                    <p className="analysis-text">{lifestyle.text}</p>
                    
                    {/* 品牌价格区间展示 */}
                    {analysis.lifestyle?.brands_info?.items?.length > 0 && (
                      <div className="brands-section">
                        <div className="brands-header">
                          <span className="brands-icon">🏷️</span>
                          <span className="brands-title">识别到的品牌</span>
                          {analysis.lifestyle.brands_info.highest_tier && (
                            <span className={`tier-badge tier-${analysis.lifestyle.brands_info.highest_tier.includes('奢') ? 'luxury' : analysis.lifestyle.brands_info.highest_tier.includes('轻奢') ? 'light' : 'normal'}`}>
                              {analysis.lifestyle.brands_info.highest_tier}
                            </span>
                          )}
                        </div>
                        <div className="brands-list">
                          {analysis.lifestyle.brands_info.items.map((item, idx) => (
                            <div key={idx} className={`brand-item brand-${item.tier.includes('奢') ? 'luxury' : item.tier.includes('轻奢') ? 'light' : item.tier.includes('运动') ? 'sport' : 'normal'}`}>
                              <span className="brand-name">{item.brand}</span>
                              <span className="brand-tier">{item.tier}</span>
                              <span className="brand-price">{item.price_range}</span>
                            </div>
                          ))}
                        </div>
                        <div className="brands-summary">{analysis.lifestyle.brands_info.summary}</div>
                      </div>
                    )}
                    
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
                          推断{analysis.room_analysis.inferred_people_count}
                        </span>
                      )}
                      {analysis.lifestyle?.consumption_level && 
                       analysis.lifestyle.consumption_level !== '无法判断' && (
                        <span className="analysis-tag">
                          <span className="tag-icon">💰</span>
                          {analysis.lifestyle.consumption_level}
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
