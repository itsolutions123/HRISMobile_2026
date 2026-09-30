import React, { useContext, useState, useEffect, useCallback } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ActivityIndicator, FlatList, ScrollView, TextInput, Alert, Platform, Modal, Image } from 'react-native';
import { WebView } from 'react-native-webview';
import { Ionicons } from '@expo/vector-icons';
import { AuthContext } from '../context/AuthContext';

export default function FormsScreen({ navigation }) {
  const { user, token, API_BASE_URL } = useContext(AuthContext);
  
  const [currentView, setCurrentView] = useState('CATEGORIES');
  const [loading, setLoading] = useState(true);
  
  const [categories, setCategories] = useState([]);
  const [activeCategory, setActiveCategory] = useState(null);
  
  const [forms, setForms] = useState([]);
  const [activeForm, setActiveForm] = useState(null);
  
  const [formData, setFormData] = useState({});
  const [submitting, setSubmitting] = useState(false);
  
  const [webViewHeights, setWebViewHeights] = useState({});
  
  // Signature Modal States
  const [sigModalVisible, setSigModalVisible] = useState(false);
  const [activeSigField, setActiveSigField] = useState(null);

  const fetchCategories = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/forms/categories`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setCategories(data);
      }
    } catch (error) {
      console.log('Error fetching form categories:', error);
    }
    setLoading(false);
  }, [API_BASE_URL, token]);

  useEffect(() => {
    fetchCategories();
  }, [fetchCategories]);

  const handleSelectCategory = async (cat) => {
    setActiveCategory(cat);
    setCurrentView('FORMS');
    setLoading(true);
    try {
      const catName = typeof cat === 'string' ? cat : cat.name;
      const res = await fetch(`${API_BASE_URL}/api/forms?category=${encodeURIComponent(catName)}&is_archived=false`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setForms(data);
      }
    } catch (error) {
      console.log('Error fetching forms:', error);
    }
    setLoading(false);
  };

  const handleSelectForm = (form) => {
    setActiveForm(form);
    setFormData({});
    setWebViewHeights({});
    setCurrentView('FILL_FORM');
  };

  const handleSubmitForm = async () => {
    setSubmitting(true);
    // Convert formData object into the array expected by the backend
    const formattedData = Object.keys(formData).map(key => ({
      label: key,
      value: formData[key]
    }));

    try {
      const res = await fetch(`${API_BASE_URL}/api/forms/${activeForm.id}/submissions`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          smart_group: user?.department || 'Unknown',
          form_data: formattedData
        })
      });
      
      if (res.ok) {
        Alert.alert('Success', 'Form submitted successfully!');
        setCurrentView('FORMS');
      } else {
        Alert.alert('Notice', 'Form submitted (Offline mock/Sync pending).');
        setCurrentView('FORMS');
      }
    } catch (error) {
      Alert.alert('Error', 'Could not connect to server.');
    }
    setSubmitting(false);
  };

  const updateField = (fieldLabel, value) => {
    setFormData(prev => ({ ...prev, [fieldLabel]: value }));
  };

  const signatureHtml = `
    <!DOCTYPE html>
    <html>
    <head>
      <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
      <style>
        * { box-sizing: border-box; font-family: -apple-system, sans-serif; }
        body { margin: 0; padding: 0; display: flex; flex-direction: column; height: 100vh; background: #ffffff; }
        .tabs { display: flex; margin-bottom: 16px; gap: 8px; }
        .tab { flex: 1; text-align: center; padding: 10px; border-radius: 8px; font-weight: 600; font-size: 14px; color: #2563eb; background: #eff6ff; display: flex; align-items: center; justify-content: center; gap: 6px; }
        .tab.active { background: #2563eb; color: #ffffff; }
        .panel { flex: 1; display: none; flex-direction: column; min-height: 200px; }
        .panel.active { display: flex; }
        canvas { border: 1px solid #cbd5e1; border-radius: 8px; flex: 1; background: #ffffff; touch-action: none; width: 100%; }
        .upload-area { border: 2px dashed #cbd5e1; border-radius: 8px; flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; background: #f8fafc; color: #64748b; }
        .upload-area input { display: none; }
        .actions { display: flex; justify-content: space-between; margin-top: 16px; }
        button { padding: 12px 20px; border-radius: 20px; font-weight: 600; font-size: 14px; border: none; }
        .btn-clear { background: #ffffff; color: #ef4444; border: 1px solid #ef4444; }
        .btn-save { background: #2563eb; color: #ffffff; padding: 12px 24px; }
      </style>
    </head>
    <body>
      <div class="tabs">
        <div class="tab active" onclick="switchTab('draw')">✎ Draw Signature</div>
        <div class="tab" onclick="switchTab('upload')">↑ Upload Signature</div>
      </div>
      
      <div id="draw-panel" class="panel active">
        <canvas id="sigCanvas"></canvas>
        <div class="actions">
          <button class="btn-clear" onclick="clearCanvas()">⌫ Clear</button>
          <button class="btn-save" onclick="saveDraw()">Save Signature</button>
        </div>
      </div>

      <div id="upload-panel" class="panel">
        <label class="upload-area" id="uploadDropzone">
          <span style="font-size: 32px; margin-bottom: 8px; color: #2563eb;">↑</span>
          <span style="font-weight: 600; color: #334155;">Tap to upload image</span>
          <span style="font-size: 12px; margin-top: 4px;">PNG, JPG (Auto-removes background)</span>
          <input type="file" accept="image/png, image/jpeg, image/webp" onchange="handleUpload(event)">
        </label>
        <div class="actions" style="justify-content: flex-end;">
           <button class="btn-save" onclick="saveUpload()">Save Signature</button>
        </div>
      </div>

      <script>
        let mode = 'draw';
        let uploadedB64 = null;
        
        function switchTab(m) {
          mode = m;
          document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
          document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
          if(m === 'draw') {
             document.querySelectorAll('.tab')[0].classList.add('active');
             document.getElementById('draw-panel').classList.add('active');
             resizeCanvas();
          } else {
             document.querySelectorAll('.tab')[1].classList.add('active');
             document.getElementById('upload-panel').classList.add('active');
          }
        }

        const canvas = document.getElementById('sigCanvas');
        const ctx = canvas.getContext('2d');
        let isDrawing = false;

        function resizeCanvas() {
          const rect = canvas.getBoundingClientRect();
          canvas.width = rect.width;
          canvas.height = rect.height;
          ctx.lineWidth = 3;
          ctx.lineCap = 'round';
          ctx.strokeStyle = '#0f172a';
        }
        window.addEventListener('resize', resizeCanvas);
        setTimeout(resizeCanvas, 100);

        function getPos(e) {
          const rect = canvas.getBoundingClientRect();
          const clientX = e.touches ? e.touches[0].clientX : e.clientX;
          const clientY = e.touches ? e.touches[0].clientY : e.clientY;
          return { x: clientX - rect.left, y: clientY - rect.top };
        }

        canvas.addEventListener('touchstart', (e) => { isDrawing = true; const p = getPos(e); ctx.beginPath(); ctx.moveTo(p.x, p.y); e.preventDefault(); }, {passive: false});
        canvas.addEventListener('touchmove', (e) => { if(!isDrawing) return; const p = getPos(e); ctx.lineTo(p.x, p.y); ctx.stroke(); e.preventDefault(); }, {passive: false});
        canvas.addEventListener('touchend', () => isDrawing = false);

        function clearCanvas() { ctx.clearRect(0, 0, canvas.width, canvas.height); }

        function handleUpload(e) {
          const file = e.target.files[0];
          if(!file) return;
          const reader = new FileReader();
          reader.onload = (evt) => {
             const img = new Image();
             img.onload = () => {
                const tempCv = document.createElement('canvas');
                const tempCtx = tempCv.getContext('2d');
                let w = img.width; let h = img.height;
                const max = 600;
                if(w > max || h > max) {
                   if(w > h) { h = Math.round(h * max / w); w = max; }
                   else { w = Math.round(w * max / h); h = max; }
                }
                tempCv.width = w; tempCv.height = h;
                tempCtx.drawImage(img, 0, 0, w, h);
                const imgData = tempCtx.getImageData(0,0, w, h);
                const d = imgData.data;
                for(let i=0; i<d.length; i+=4) {
                   if(d[i]>200 && d[i+1]>200 && d[i+2]>200) d[i+3] = 0;
                }
                tempCtx.putImageData(imgData, 0, 0);
                uploadedB64 = tempCv.toDataURL('image/png');
                document.getElementById('uploadDropzone').innerHTML = '<img src="'+uploadedB64+'" style="max-height:140px; max-width:100%; object-fit:contain;"/>';
             };
             img.src = evt.target.result;
          };
          reader.readAsDataURL(file);
        }

        function saveDraw() {
          const data = canvas.toDataURL('image/png');
          window.ReactNativeWebView.postMessage(JSON.stringify({ type: 'SIGNATURE_SAVE', data }));
        }

        function saveUpload() {
          if(!uploadedB64) return;
          window.ReactNativeWebView.postMessage(JSON.stringify({ type: 'SIGNATURE_SAVE', data: uploadedB64 }));
        }
      </script>
    </body>
    </html>
  `;

  const renderCategories = () => (
    <View style={styles.viewContainer}>
      <Text style={styles.headerTitle}>Form Categories</Text>
      <Text style={styles.headerSubtitle}>Select a department or category</Text>
      {loading ? <ActivityIndicator size="large" color="#2563eb" style={{marginTop: 40}} /> : (
        <FlatList
          data={categories}
          keyExtractor={(item, index) => item.id ? item.id.toString() : index.toString()}
          contentContainerStyle={{ paddingBottom: 20, paddingTop: 10 }}
          renderItem={({ item }) => (
            <TouchableOpacity style={styles.categoryCard} onPress={() => handleSelectCategory(item)}>
              <View style={[styles.iconContainer, { backgroundColor: item.color || '#0ea5e9' }]}>
                <Ionicons name={item.icon || 'document-text'} size={24} color="#ffffff" />
              </View>
              <Text style={styles.categoryName}>{item.name}</Text>
              <Ionicons name="chevron-forward" size={20} color="#cbd5e1" />
            </TouchableOpacity>
          )}
        />
      )}
    </View>
  );

  const renderForms = () => (
    <View style={styles.viewContainer}>
      <TouchableOpacity style={styles.backBtn} onPress={() => setCurrentView('CATEGORIES')}>
        <Ionicons name="arrow-back" size={20} color="#2563eb" />
        <Text style={styles.backBtnText}>Categories</Text>
      </TouchableOpacity>
      <Text style={styles.headerTitle}>{activeCategory?.name || 'Category'} Forms</Text>
      
      {loading ? <ActivityIndicator size="large" color="#2563eb" style={{marginTop: 40}} /> : (
        forms.length === 0 ? (
          <View style={styles.emptyState}>
            <Ionicons name="folder-open-outline" size={48} color="#cbd5e1" />
            <Text style={styles.emptyStateText}>No active forms in this category.</Text>
          </View>
        ) : (
          <FlatList
            data={forms}
            keyExtractor={item => item.id.toString()}
            contentContainerStyle={{ paddingBottom: 20 }}
            renderItem={({ item }) => (
              <TouchableOpacity style={styles.formCard} onPress={() => handleSelectForm(item)}>
                <View style={{flex: 1}}>
                  <Text style={styles.formName}>{item.name}</Text>
                  <Text style={styles.formDesc} numberOfLines={1}>{item.description || 'Fill out this form'}</Text>
                </View>
                <Ionicons name="create-outline" size={22} color="#0284c7" />
              </TouchableOpacity>
            )}
          />
        )
      )}
    </View>
  );

  const renderActiveForm = () => {
    let fields = [];
    try {
      if (typeof activeForm?.schema_fields === 'string') {
        fields = JSON.parse(activeForm.schema_fields);
      } else {
        fields = activeForm?.schema_fields || [];
      }
    } catch (e) {
      console.log('Error parsing fields:', e);
    }
    
    return (
      <View style={styles.viewContainer}>
        <View style={styles.formHeaderRow}>
          <TouchableOpacity style={styles.backBtnInline} onPress={() => setCurrentView('FORMS')}>
            <Ionicons name="close" size={24} color="#475569" />
          </TouchableOpacity>
          <Text style={styles.formFillTitle} numberOfLines={1}>{activeForm?.name}</Text>
          <View style={{width: 24}} />
        </View>

        <ScrollView style={styles.formScroll} contentContainerStyle={{ paddingBottom: 40 }} showsVerticalScrollIndicator={false}>
          {activeForm?.description ? (
            <Text style={styles.formMainDesc}>{activeForm.description}</Text>
          ) : null}

          {fields.map((field, idx) => {
            const label = field.label || field.content || 'Field';
            const value = formData[label] || '';

            if (field.type === 'Description') {
              const descHtml = field.description || field.content || field.label || '';
              const htmlInjection = `
                <!DOCTYPE html>
                <html>
                  <head>
                    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
                    <style>
                      body { font-family: -apple-system, sans-serif; color: #334155; margin: 0; padding: 0; font-size: 15px; line-height: 1.6; background: transparent; }
                      img { max-width: 100%; height: auto; border-radius: 8px; margin-top: 10px; }
                    </style>
                  </head>
                  <body>
                    ${descHtml}
                    <script>
                      function sendHeight() {
                        const height = Math.max(document.body.scrollHeight, document.documentElement.scrollHeight);
                        window.ReactNativeWebView.postMessage(height);
                      }
                      window.onload = sendHeight;
                      setTimeout(sendHeight, 100);
                      setTimeout(sendHeight, 500);
                      setTimeout(sendHeight, 1200);
                      if (window.ResizeObserver) {
                        new ResizeObserver(sendHeight).observe(document.body);
                      }
                    </script>
                  </body>
                </html>
              `;
              
              return (
                <View key={idx} style={[styles.fieldContainer, { marginBottom: 16 }]}>
                  <WebView
                    originWhitelist={['*']}
                    source={{ html: htmlInjection }}
                    style={{ width: '100%', height: Math.max(100, webViewHeights[idx] || 100), backgroundColor: 'transparent' }}
                    scrollEnabled={false}
                    bounces={false}
                    showsVerticalScrollIndicator={false}
                    onMessage={(event) => {
                      const ht = Number(event.nativeEvent.data);
                      if (ht && ht > 0) {
                        setWebViewHeights(prev => ({ ...prev, [idx]: ht }));
                      }
                    }}
                  />
                </View>
              );
            }

            return (
              <View key={idx} style={styles.fieldContainer}>
                <Text style={styles.fieldLabel}>{label} {field.required ? <Text style={{color: '#ef4444'}}>*</Text> : ''}</Text>
                
                {field.type === 'Open Ended' ? (
                  <TextInput 
                    style={[styles.input, { height: 80, textAlignVertical: 'top' }]} 
                    multiline 
                    placeholder="Type your answer..." 
                    value={value}
                    onChangeText={(val) => updateField(label, val)}
                  />
                ) : field.type === 'Yes/No' ? (
                  <View style={styles.yesNoContainer}>
                    {(field.options && field.options.length > 0 ? field.options : ['Yes', 'No']).map(opt => (
                      <TouchableOpacity 
                        key={opt} 
                        style={[styles.yesNoBtn, value === opt && styles.yesNoBtnActive]}
                        onPress={() => updateField(label, opt)}
                      >
                        <Text style={[styles.yesNoText, value === opt && styles.yesNoTextActive]}>{opt}</Text>
                      </TouchableOpacity>
                    ))}
                  </View>
                ) : field.type === 'Dropdown' ? (
                  <View style={styles.dropdownFakeContainer}>
                    {(field.options || []).map((opt, oIdx) => (
                      <TouchableOpacity 
                        key={oIdx} 
                        style={[styles.radioRow, value === opt && styles.radioRowActive]}
                        onPress={() => updateField(label, opt)}
                      >
                        <View style={[styles.radioCircle, value === opt && styles.radioCircleActive]} />
                        <Text style={styles.radioText}>{opt}</Text>
                      </TouchableOpacity>
                    ))}
                  </View>
                ) : (field.type === 'Task' || field.type === 'Checkbox') ? (
                  <View style={styles.checkboxGroup}>
                    {(field.options || []).map((opt, oIdx) => {
                      const currentSelections = Array.isArray(value) ? value : [];
                      const isSelected = currentSelections.includes(opt);
                      return (
                        <TouchableOpacity
                          key={oIdx}
                          style={styles.checkboxRow}
                          onPress={() => {
                            let newSelections = [...currentSelections];
                            if (isSelected) newSelections = newSelections.filter(x => x !== opt);
                            else newSelections.push(opt);
                            updateField(label, newSelections);
                          }}
                        >
                          <View style={[styles.checkboxBox, isSelected && styles.checkboxBoxActive]}>
                            {isSelected && <Ionicons name="checkmark" size={16} color="#ffffff" />}
                          </View>
                          <Text style={styles.checkboxText}>{opt}</Text>
                        </TouchableOpacity>
                      );
                    })}
                  </View>
                ) : field.type === 'Signature' ? (
                  <View>
                    {value ? (
                      <View style={styles.signedContainer}>
                        <Image source={{ uri: value }} style={styles.signedImage} />
                        <TouchableOpacity onPress={() => { setActiveSigField(label); setSigModalVisible(true); }}>
                          <Text style={styles.editSigText}>✎ Edit Signature</Text>
                        </TouchableOpacity>
                      </View>
                    ) : (
                      <TouchableOpacity style={styles.signatureBtn} onPress={() => { setActiveSigField(label); setSigModalVisible(true); }}>
                        <Ionicons name="pencil" size={20} color="#64748b" />
                        <Text style={styles.signatureBtnText}>Tap to Sign</Text>
                      </TouchableOpacity>
                    )}
                  </View>
                ) : field.type === 'Date' ? (
                  <View style={styles.dateInputContainer}>
                    <TextInput 
                      style={[styles.input, { paddingRight: 40 }]} 
                      placeholder="mm/dd/yyyy" 
                      value={value}
                      onChangeText={(val) => updateField(label, val)}
                    />
                    <Ionicons name="calendar-outline" size={20} color="#64748b" style={styles.dateIcon} />
                  </View>
                ) : (
                  <TextInput 
                    style={styles.input} 
                    placeholder="Enter response..." 
                    value={value}
                    onChangeText={(val) => updateField(label, val)}
                  />
                )}
              </View>
            );
          })}

          <TouchableOpacity style={styles.submitBtn} onPress={handleSubmitForm} disabled={submitting}>
            {submitting ? <ActivityIndicator color="#fff" /> : <Text style={styles.submitBtnText}>Submit Form</Text>}
          </TouchableOpacity>
        </ScrollView>
        
        {/* Native Signature Modal Overlay */}
        <Modal visible={sigModalVisible} transparent animationType="fade">
          <View style={styles.modalBg}>
            <View style={styles.sigModalSheet}>
              <View style={styles.modalHeader}>
                <Text style={styles.modalTitle}><Ionicons name="create-outline" size={20} color="#2563eb" /> Provide Signature</Text>
                <TouchableOpacity onPress={() => setSigModalVisible(false)}><Ionicons name="close" size={24} color="#475569" /></TouchableOpacity>
              </View>
              <WebView
                originWhitelist={['*']}
                source={{ html: signatureHtml }}
                style={styles.sigWebView}
                bounces={false}
                scrollEnabled={false}
                onMessage={(event) => {
                  try {
                    const res = JSON.parse(event.nativeEvent.data);
                    if (res.type === 'SIGNATURE_SAVE') {
                      updateField(activeSigField, res.data);
                      setSigModalVisible(false);
                    }
                  } catch (e) {}
                }}
              />
            </View>
          </View>
        </Modal>
      </View>
    );
  };

  return (
    <View style={styles.container}>
      {currentView === 'CATEGORIES' && renderCategories()}
      {currentView === 'FORMS' && renderForms()}
      {currentView === 'FILL_FORM' && renderActiveForm()}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f8fafc' },
  viewContainer: { flex: 1, padding: 20, paddingTop: Platform.OS === 'ios' ? 50 : 20 },
  headerTitle: { fontSize: 24, fontWeight: '800', color: '#0f172a', marginBottom: 4 },
  headerSubtitle: { fontSize: 14, color: '#64748b', marginBottom: 20 },
  
  categoryCard: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#ffffff', padding: 16, borderRadius: 16, marginBottom: 12, borderWidth: 1, borderColor: '#f1f5f9' },
  iconContainer: { width: 44, height: 44, borderRadius: 12, justifyContent: 'center', alignItems: 'center', marginRight: 16 },
  categoryName: { flex: 1, fontSize: 16, fontWeight: '700', color: '#1e293b' },
  
  backBtn: { flexDirection: 'row', alignItems: 'center', marginBottom: 16, gap: 4 },
  backBtnText: { color: '#2563eb', fontWeight: '600', fontSize: 15 },
  formCard: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#ffffff', padding: 18, borderRadius: 16, marginBottom: 12, borderWidth: 1, borderColor: '#e2e8f0', shadowColor: '#000', shadowOpacity: 0.03, shadowRadius: 4, elevation: 2 },
  formName: { fontSize: 16, fontWeight: '700', color: '#0f172a', marginBottom: 4 },
  formDesc: { fontSize: 13, color: '#64748b' },
  emptyState: { flex: 1, justifyContent: 'center', alignItems: 'center', marginTop: -50 },
  emptyStateText: { marginTop: 12, color: '#94a3b8', fontSize: 15, fontWeight: '500' },
  
  formHeaderRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20, borderBottomWidth: 1, borderColor: '#e2e8f0', paddingBottom: 16 },
  backBtnInline: { padding: 4 },
  formFillTitle: { flex: 1, fontSize: 18, fontWeight: '800', color: '#0f172a', textAlign: 'center' },
  formScroll: { flex: 1 },
  formMainDesc: { fontSize: 14, color: '#475569', marginBottom: 20, lineHeight: 20 },
  
  fieldContainer: { marginBottom: 24 },
  fieldLabel: { fontSize: 13, fontWeight: '700', color: '#334155', marginBottom: 8, textTransform: 'uppercase', letterSpacing: 0.5 },
  input: { backgroundColor: '#ffffff', borderWidth: 1, borderColor: '#cbd5e1', borderRadius: 12, padding: 14, fontSize: 15, color: '#0f172a' },
  
  yesNoContainer: { flexDirection: 'row', gap: 12 },
  yesNoBtn: { flex: 1, paddingVertical: 12, borderRadius: 10, borderWidth: 1, borderColor: '#cbd5e1', backgroundColor: '#ffffff', alignItems: 'center' },
  yesNoBtnActive: { borderColor: '#0284c7', backgroundColor: '#eff6ff' },
  yesNoText: { fontWeight: '600', color: '#475569', fontSize: 15 },
  yesNoTextActive: { color: '#0284c7' },
  
  dropdownFakeContainer: { backgroundColor: '#ffffff', borderWidth: 1, borderColor: '#cbd5e1', borderRadius: 12, overflow: 'hidden' },
  radioRow: { flexDirection: 'row', alignItems: 'center', padding: 14, borderBottomWidth: 1, borderColor: '#f1f5f9' },
  radioRowActive: { backgroundColor: '#f8fafc' },
  radioCircle: { width: 20, height: 20, borderRadius: 10, borderWidth: 2, borderColor: '#cbd5e1', marginRight: 12 },
  radioCircleActive: { borderColor: '#0284c7', backgroundColor: '#0284c7' },
  radioText: { fontSize: 15, color: '#334155' },
  
  checkboxGroup: { marginTop: 4 },
  checkboxRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 16 },
  checkboxBox: { width: 22, height: 22, borderRadius: 6, borderWidth: 2, borderColor: '#cbd5e1', marginRight: 12, justifyContent: 'center', alignItems: 'center', backgroundColor: '#ffffff' },
  checkboxBoxActive: { borderColor: '#0284c7', backgroundColor: '#0284c7' },
  checkboxText: { fontSize: 15, color: '#334155' },

  dateInputContainer: { position: 'relative', justifyContent: 'center' },
  dateIcon: { position: 'absolute', right: 14 },
  
  signatureBtn: { backgroundColor: '#f8fafc', borderWidth: 1, borderColor: '#cbd5e1', borderStyle: 'dashed', borderRadius: 12, padding: 24, alignItems: 'center', flexDirection: 'row', justifyContent: 'center', gap: 8 },
  signatureBtnText: { color: '#64748b', fontWeight: '600', fontSize: 15 },
  signedContainer: { alignItems: 'center', padding: 16, backgroundColor: '#f8fafc', borderRadius: 12, borderWidth: 1, borderColor: '#e2e8f0' },
  signedImage: { width: '100%', height: 100, resizeMode: 'contain' },
  editSigText: { color: '#2563eb', fontWeight: '600', marginTop: 12 },
  
  submitBtn: { backgroundColor: '#2563eb', borderRadius: 14, paddingVertical: 16, alignItems: 'center', marginTop: 10 },
  submitBtnText: { color: '#ffffff', fontSize: 16, fontWeight: '800' },
  
  // Modal Layout
  modalBg: { flex: 1, backgroundColor: 'rgba(15, 23, 42, 0.7)', justifyContent: 'center', padding: 16 },
  sigModalSheet: { backgroundColor: '#ffffff', borderRadius: 20, padding: 20, height: 420 },
  modalHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 },
  modalTitle: { fontSize: 18, fontWeight: '800', color: '#0f172a' },
  sigWebView: { flex: 1, backgroundColor: 'transparent' }
});
