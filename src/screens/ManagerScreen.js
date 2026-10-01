import React, { useState, useEffect, useContext } from 'react';
import { View, Text, StyleSheet, FlatList, TouchableOpacity, ActivityIndicator, Alert, RefreshControl, TextInput, Modal, Platform } from 'react-native';
import { AuthContext } from '../context/AuthContext';
import * as FileSystem from 'expo-file-system';
import * as Sharing from 'expo-sharing';
import { Ionicons } from '@expo/vector-icons';

export default function ManagerScreen() {
  const { user, API_BASE_URL, token } = useContext(AuthContext);
  
  // Views
  const [currentView, setCurrentView] = useState('MENU'); 
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const [revisions, setRevisions] = useState([]);
  const [team, setTeam] = useState([]);
  const [groups, setGroups] = useState([]);
  const [expandedBrand, setExpandedBrand] = useState(null);
  const [teamSearchQuery, setTeamSearchQuery] = useState('');
  const [teamTab, setTeamTab] = useState('USERS');

  // Mock Attendance Stats (To be replaced with real endpoint data)
  const [attendanceStats, setAttendanceStats] = useState({ clockedIn: 12, total: 45 });

  // Modal Action States for Manager Signature & Note
  const [selectedRevision, setSelectedRevision] = useState(null);
  const [showActionModal, setShowActionModal] = useState(false);
  const [actionType, setActionType] = useState('APPROVED');
  const [managerSignature, setManagerSignature] = useState('');
  const [managerNote, setManagerNote] = useState('');
  const [submittingAction, setSubmittingAction] = useState(false);

  // Date range states for Export UI
  const [startDate, setStartDate] = useState(new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]);
  const [endDate, setEndDate] = useState(new Date().toISOString().split('T')[0]);
  const [exporting, setExporting] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    try {
      if (currentView === 'ATTENDANCE' || currentView === 'MENU') {
        const res = await fetch(`${API_BASE_URL}/api/manager/revisions`, { headers: { 'Authorization': `Bearer ${token}` }});
        if (res.ok) setRevisions(await res.json());
      } 
      if (currentView === 'TEAM' || currentView === 'MENU') {
        const res = await fetch(`${API_BASE_URL}/api/manager/team`, { headers: { 'Authorization': `Bearer ${token}` }});
        if (res.ok) {
          const t = await res.json();
          setTeam(t);
          setAttendanceStats(prev => ({ ...prev, total: t.length || 45 }));
        }
      } 
      if (currentView === 'GROUPS') {
        // Fetch all groups and dynamically categorize them by Brand
        const res = await fetch(`${API_BASE_URL}/api/jobs/groups`, { headers: { 'Authorization': `Bearer ${token}` }});
        if (res.ok) {
          const data = await res.json();
          const brandsMap = {};
          
          data.forEach(g => {
            const bName = g.brand || g.brand_name || 'HEAD OFFICE';
            if (!brandsMap[bName]) brandsMap[bName] = [];
            brandsMap[bName].push(g);
          });
          
          const structured = Object.keys(brandsMap).map((b, i) => ({
            id: `brand-${i}`,
            brand: b,
            subGroups: brandsMap[b]
          }));
          
          setGroups(structured);
        }
      }
    } catch (error) {
      console.log('Error fetching manager data:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [currentView]);

  const onRefresh = () => {
    setRefreshing(true);
    fetchData();
  };

  const openActionModal = (item, type) => {
    setSelectedRevision(item);
    setActionType(type);
    setManagerSignature(user?.name || '');
    setManagerNote('');
    setShowActionModal(true);
  };

  const handleConfirmRevisionAction = async () => {
    if (!selectedRevision) return;
    if (!managerSignature.trim()) {
      Alert.alert('Signature Required', 'Please type your signature/name to sign the review request.');
      return;
    }

    setSubmittingAction(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/manager/revisions/${selectedRevision.id}/action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({
          action: actionType,
          manager_signature: managerSignature,
          manager_note: managerNote
        }),
      });
      if (res.ok) {
        Alert.alert('Success', `Shift revision request ${actionType.toLowerCase()} successfully.`);
        setShowActionModal(false);
        setSelectedRevision(null);
        fetchData();
      } else {
        const err = await res.json();
        Alert.alert('Error', err.detail || 'Failed to process request');
      }
    } catch (err) {
      Alert.alert('Error', 'Network or server error');
    } finally {
      setSubmittingAction(false);
    }
  };

  const handleExportTimesheet = async () => {
    if (!startDate || !endDate) {
      Alert.alert('Validation Error', 'Please select both start and end dates.');
      return;
    }
    setExporting(true);
    try {
      const exportUrl = `${API_BASE_URL}/api/punch/export?start_date=${startDate}&end_date=${endDate}`;
      const fileUri = FileSystem.documentDirectory + `timesheet_export_${Date.now()}.csv`;
      
      const downloadRes = await FileSystem.downloadAsync(exportUrl, fileUri, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (downloadRes.status === 200) {
        const canShare = await Sharing.isAvailableAsync();
        if (canShare) {
          await Sharing.shareAsync(downloadRes.uri);
        } else {
          Alert.alert('Success', 'File downloaded to: ' + downloadRes.uri);
        }
      } else {
        Alert.alert('Export Error', 'Download failed with status: ' + downloadRes.status);
      }
    } catch (err) {
      Alert.alert('Export Error', 'Failed to trigger file download.');
    } finally {
      setExporting(false);
    }
  };

  const handleArchiveUser = (userItem) => {
    Alert.alert(
      "Archive User",
      `Are you sure you want to archive ${userItem.name}?`,
      [
        { text: "Cancel", style: "cancel" },
        { text: "Archive", style: "destructive", onPress: () => alert('Archive functionality coming soon!') }
      ]
    );
  };

  const renderMenu = () => (
    <View style={styles.menuContainer}>
      <TouchableOpacity style={styles.attendanceCard} onPress={() => setCurrentView('ATTENDANCE')}>
        <Text style={styles.cardHeaderTitle}>ATTENDANCE</Text>
        <Text style={styles.attendanceStatsText}>{attendanceStats.clockedIn} / {attendanceStats.total}</Text>
        {revisions.length > 0 && (
          <View style={styles.pendingAlertBadge}>
            <Text style={styles.pendingAlertText}>{revisions.length} Pending Revisions</Text>
          </View>
        )}
      </TouchableOpacity>

      <TouchableOpacity style={styles.menuBtn} onPress={() => setCurrentView('GROUPS')}>
        <Text style={styles.menuBtnText}>SMART GROUPS</Text>
        <Ionicons name="chevron-forward" size={20} color="#cbd5e1" />
      </TouchableOpacity>

      <TouchableOpacity style={styles.menuBtn} onPress={() => setCurrentView('TEAM')}>
        <Text style={styles.menuBtnText}>USERS & DIRECTORY</Text>
        <Ionicons name="chevron-forward" size={20} color="#cbd5e1" />
      </TouchableOpacity>

      <TouchableOpacity style={styles.menuBtn} onPress={() => setCurrentView('EXPORT')}>
        <Text style={styles.menuBtnText}>EXPORT DTR</Text>
        <Ionicons name="chevron-forward" size={20} color="#cbd5e1" />
      </TouchableOpacity>
    </View>
  );

  const renderHeader = (title) => (
    <View style={styles.subViewHeader}>
      <TouchableOpacity style={styles.backBtn} onPress={() => setCurrentView('MENU')}>
        <Ionicons name="arrow-back" size={24} color="#2563eb" />
      </TouchableOpacity>
      <Text style={styles.subViewTitle}>{title}</Text>
    </View>
  );

  const renderRevisionItem = ({ item }) => (
    <View style={styles.itemCard}>
      <View style={styles.cardHeader}>
        <Text style={styles.cardTitle}>{item.employee_name} ({item.employee_id})</Text>
        <Text style={styles.pendingBadge}>{item.status}</Text>
      </View>
      <Text style={styles.cardDetail}>Smart Group: <Text style={styles.boldText}>{item.smart_group || 'General'}</Text></Text>
      <Text style={styles.cardDetail}>Type: <Text style={styles.boldText}>{item.requested_punch_type}</Text></Text>
      <Text style={styles.cardDetail}>Requested Time: {new Date(item.requested_timestamp).toLocaleString()}</Text>
      <Text style={styles.cardDetail}>Reason: {item.reason}</Text>

      <View style={styles.actionRow}>
        <TouchableOpacity style={[styles.actionBtn, styles.approveBtn]} onPress={() => openActionModal(item, 'APPROVED')}>
          <Text style={styles.btnText}>Approve & Sign</Text>
        </TouchableOpacity>
        <TouchableOpacity style={[styles.actionBtn, styles.rejectBtn]} onPress={() => openActionModal(item, 'REJECTED')}>
          <Text style={styles.btnText}>Reject</Text>
        </TouchableOpacity>
      </View>
    </View>
  );

  const renderTeamItem = ({ item }) => (
    <View style={styles.itemCard}>
      <View style={{flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start'}}>
        <View style={{flex: 1}}>
          <Text style={styles.cardTitle}>{item.name}</Text>
          <Text style={styles.cardDetail}>ID: {item.employee_id} | Role: {item.role}</Text>
          <Text style={styles.cardDetail}>Position: {item.position || 'N/A'}</Text>
          <Text style={styles.cardDetail}>Department: {item.department || 'N/A'}</Text>
        </View>
        {teamTab === 'USERS' && (
          <TouchableOpacity onPress={() => handleArchiveUser(item)} style={{padding: 8}}>
            <Ionicons name="archive-outline" size={22} color="#ef4444" />
          </TouchableOpacity>
        )}
      </View>
    </View>
  );

  const renderGroupItem = ({ item }) => {
    const isExpanded = expandedBrand === item.id;
    return (
      <View style={{ marginBottom: isExpanded ? 16 : 0 }}>
        <TouchableOpacity 
          style={[styles.brandCard, { 
            marginBottom: isExpanded ? 0 : 16, 
            borderBottomLeftRadius: isExpanded ? 0 : 16, 
            borderBottomRightRadius: isExpanded ? 0 : 16 
          }]} 
          onPress={() => setExpandedBrand(isExpanded ? null : item.id)}
          activeOpacity={0.8}
        >
          <Text style={styles.brandCardText}>{item.brand}</Text>
          <Ionicons 
            name={isExpanded ? "chevron-up" : "chevron-down"} 
            size={24} 
            color="#0f172a" 
            style={{position: 'absolute', right: 20}} 
          />
        </TouchableOpacity>
        
        {isExpanded && (
          <View style={styles.subGroupsContainer}>
            {item.subGroups.map((sg, idx) => (
              <View key={idx} style={[styles.subGroupRow, idx === item.subGroups.length - 1 && { borderBottomWidth: 0 }]}>
                <View style={styles.subGroupDot} />
                <Text style={styles.subGroupText}>{sg.name || sg.dept}</Text>
              </View>
            ))}
          </View>
        )}
      </View>
    );
  };

  const renderExportView = () => (
    <View style={styles.exportCard}>
      <Text style={styles.exportTitle}>Payroll & Timesheet Export</Text>
      <Text style={styles.exportSubtitle}>Generate Excel (.xlsx) report for date range:</Text>

      <View style={styles.inputGroup}>
        <Text style={styles.label}>Start Date (YYYY-MM-DD):</Text>
        <TextInput
          style={styles.input}
          value={startDate}
          onChangeText={setStartDate}
          placeholder="YYYY-MM-DD"
        />
      </View>

      <View style={styles.inputGroup}>
        <Text style={styles.label}>End Date (YYYY-MM-DD):</Text>
        <TextInput
          style={styles.input}
          value={endDate}
          onChangeText={setEndDate}
          placeholder="YYYY-MM-DD"
        />
      </View>

      <TouchableOpacity
        style={[styles.exportBtn, exporting && styles.disabledBtn]}
        onPress={handleExportTimesheet}
        disabled={exporting}
      >
        {exporting ? (
          <ActivityIndicator color="#ffffff" />
        ) : (
          <Text style={styles.exportBtnText}>Download Timesheet (.xlsx)</Text>
        )}
      </TouchableOpacity>
    </View>
  );

  const filteredTeam = team.filter(t => {
    const match = (t.name || '').toLowerCase().includes(teamSearchQuery.toLowerCase()) || String(t.employee_id || '').includes(teamSearchQuery);
    if (teamTab === 'USERS') return match && t.status !== 'ARCHIVED' && t.status !== 'PENDING' && t.status !== 'DENIED';
    if (teamTab === 'ARCHIVED') return match && t.status === 'ARCHIVED';
    if (teamTab === 'PENDING') return match && (t.status === 'PENDING' || t.status === 'DENIED');
    return match;
  });

  const renderTeamView = () => (
    <View style={{ flex: 1 }}>
      <View style={styles.searchContainer}>
        <Ionicons name="search" size={20} color="#94a3b8" style={{marginLeft: 12}} />
        <TextInput
          style={styles.teamSearchInput}
          placeholder="Search users..."
          value={teamSearchQuery}
          onChangeText={setTeamSearchQuery}
        />
      </View>
      <View style={styles.teamTabsRow}>
        <TouchableOpacity style={[styles.teamTabBtn, teamTab === 'USERS' && styles.teamTabBtnActive]} onPress={() => setTeamTab('USERS')}>
          <Text style={[styles.teamTabText, teamTab === 'USERS' && styles.teamTabTextActive]}>Users</Text>
        </TouchableOpacity>
        <TouchableOpacity style={[styles.teamTabBtn, teamTab === 'ARCHIVED' && styles.teamTabBtnActive]} onPress={() => setTeamTab('ARCHIVED')}>
          <Text style={[styles.teamTabText, teamTab === 'ARCHIVED' && styles.teamTabTextActive]}>Archived</Text>
        </TouchableOpacity>
        <TouchableOpacity style={[styles.teamTabBtn, teamTab === 'PENDING' && styles.teamTabBtnActive]} onPress={() => setTeamTab('PENDING')}>
          <Text style={[styles.teamTabText, teamTab === 'PENDING' && styles.teamTabTextActive]}>Pending Approval</Text>
        </TouchableOpacity>
      </View>
      <FlatList
        data={filteredTeam}
        keyExtractor={(item, index) => item.employee_id ? item.employee_id.toString() : index.toString()}
        renderItem={renderTeamItem}
        contentContainerStyle={{ paddingBottom: 20 }}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
        ListEmptyComponent={<Text style={styles.emptyText}>No users found in this category.</Text>}
      />
    </View>
  );

  return (
    <View style={styles.container}>
      {currentView === 'MENU' ? (
        <>
          <Text style={styles.pageTitle}>Admin</Text>
          {loading ? <ActivityIndicator size="large" color="#2563eb" style={{marginTop: 40}}/> : renderMenu()}
        </>
      ) : (
        <>
          {renderHeader(currentView === 'ATTENDANCE' ? 'Attendance & Revisions' : currentView === 'TEAM' ? 'Users & Directory' : currentView === 'GROUPS' ? 'Smart Groups' : 'Export DTR')}
          
          {currentView === 'EXPORT' ? (
            renderExportView()
          ) : currentView === 'TEAM' ? (
            renderTeamView()
          ) : (
            <FlatList
              data={currentView === 'ATTENDANCE' ? revisions : groups}
              keyExtractor={(item, index) => typeof item === 'string' ? `${item}-${index}` : (item.id ? item.id.toString() : (item.employee_id || index).toString())}
              renderItem={currentView === 'ATTENDANCE' ? renderRevisionItem : renderGroupItem}
              contentContainerStyle={{ paddingBottom: 20 }}
              refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
              ListEmptyComponent={
                <Text style={styles.emptyText}>
                  {currentView === 'ATTENDANCE' ? 'No pending revisions.' : 'No groups available.'}
                </Text>
              }
            />
          )}
        </>
      )}

      {/* ACTION REVIEW & SIGNATURE MODAL */}
      <Modal visible={showActionModal} transparent animationType="slide">
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>
              {actionType === 'APPROVED' ? 'Approve Shift Revision' : 'Reject Shift Revision'}
            </Text>
            <Text style={styles.modalSub}>
              Employee: {selectedRevision?.employee_name} ({selectedRevision?.employee_id})
            </Text>

            <View style={styles.inputGroup}>
              <Text style={styles.label}>MANAGER SIGNATURE / NAME *</Text>
              <TextInput
                style={styles.input}
                value={managerSignature}
                onChangeText={setManagerSignature}
                placeholder="Sign or type your full name"
              />
            </View>

            <View style={styles.inputGroup}>
              <Text style={styles.label}>MANAGER NOTE / REMARKS</Text>
              <TextInput
                style={[styles.input, { height: 60, textAlignVertical: 'top' }]}
                value={managerNote}
                onChangeText={setManagerNote}
                placeholder="Add approval or rejection remarks..."
                multiline
              />
            </View>

            <View style={styles.modalActionRow}>
              <TouchableOpacity style={[styles.actionBtn, { backgroundColor: '#cbd5e1' }]} onPress={() => setShowActionModal(false)}>
                <Text style={{ color: '#334155', fontWeight: 'bold' }}>Cancel</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.actionBtn, actionType === 'APPROVED' ? styles.approveBtn : styles.rejectBtn]}
                onPress={handleConfirmRevisionAction}
                disabled={submittingAction}
              >
                {submittingAction ? (
                  <ActivityIndicator color="#ffffff" />
                ) : (
                  <Text style={styles.btnText}>
                    {actionType === 'APPROVED' ? 'Confirm Approval' : 'Confirm Rejection'}
                  </Text>
                )}
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f8fafc', paddingHorizontal: 20, paddingTop: Platform.OS === 'ios' ? 60 : 40 },
  pageTitle: { fontSize: 32, fontWeight: '800', color: '#0f172a', marginBottom: 24 },
  
  menuContainer: { flex: 1 },
  attendanceCard: { backgroundColor: '#ffffff', borderRadius: 16, padding: 24, marginBottom: 20, borderWidth: 1, borderColor: '#e2e8f0', shadowColor: '#000', shadowOpacity: 0.05, shadowRadius: 8, elevation: 3 },
  cardHeaderTitle: { fontSize: 13, fontWeight: '800', color: '#64748b', marginBottom: 16, textTransform: 'uppercase', letterSpacing: 0.5 },
  attendanceStatsText: { fontSize: 36, fontWeight: '800', color: '#0f172a', textAlign: 'center' },
  pendingAlertBadge: { backgroundColor: '#fef3c7', alignSelf: 'center', paddingHorizontal: 12, paddingVertical: 6, borderRadius: 12, marginTop: 16 },
  pendingAlertText: { color: '#d97706', fontWeight: '700', fontSize: 12 },

  menuBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', backgroundColor: '#ffffff', borderRadius: 16, padding: 20, marginBottom: 12, borderWidth: 1, borderColor: '#e2e8f0', shadowColor: '#000', shadowOpacity: 0.03, shadowRadius: 4, elevation: 2 },
  menuBtnText: { fontSize: 15, fontWeight: '700', color: '#1e293b' },

  subViewHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 20 },
  backBtn: { padding: 8, marginRight: 8 },
  subViewTitle: { fontSize: 22, fontWeight: '800', color: '#0f172a' },

  itemCard: { backgroundColor: '#ffffff', padding: 18, borderRadius: 16, marginBottom: 12, borderWidth: 1, borderColor: '#e2e8f0', shadowColor: '#000', shadowOpacity: 0.03, shadowRadius: 4, elevation: 2 },
  brandCard: { backgroundColor: '#ffffff', borderRadius: 16, paddingVertical: 40, paddingHorizontal: 20, marginBottom: 16, borderWidth: 1, borderColor: '#0f172a', justifyContent: 'center', alignItems: 'center', shadowColor: '#000', shadowOpacity: 0.05, shadowRadius: 8, elevation: 3 },
  brandCardText: { fontSize: 20, fontWeight: '800', color: '#0f172a', textTransform: 'uppercase', letterSpacing: 1, textAlign: 'center' },
  subGroupsContainer: { backgroundColor: '#f8fafc', padding: 16, borderBottomLeftRadius: 16, borderBottomRightRadius: 16, borderWidth: 1, borderTopWidth: 0, borderColor: '#0f172a' },
  subGroupRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: '#e2e8f0' },
  subGroupDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: '#2563eb', marginRight: 12 },
  subGroupText: { fontSize: 15, fontWeight: '600', color: '#334155' },
  
  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
  cardTitle: { fontWeight: '800', fontSize: 16, color: '#1e293b' },
  cardDetail: { fontSize: 13, color: '#475569', marginTop: 4 },
  boldText: { fontWeight: '700', color: '#0f172a' },
  pendingBadge: { backgroundColor: '#fef3c7', color: '#d97706', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 8, fontWeight: '700', fontSize: 11 },
  countBadge: { backgroundColor: '#e0f2fe', color: '#0369a1', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 8, fontWeight: '700', fontSize: 11 },

  actionRow: { flexDirection: 'row', marginTop: 16, gap: 12 },
  modalActionRow: { flexDirection: 'row', marginTop: 24, gap: 12 },
  actionBtn: { flex: 1, paddingVertical: 14, borderRadius: 12, alignItems: 'center', justifyContent: 'center' },
  approveBtn: { backgroundColor: '#16a34a' },
  rejectBtn: { backgroundColor: '#dc2626' },
  btnText: { color: '#ffffff', fontWeight: '800', fontSize: 14 },
  
  emptyText: { textAlign: 'center', color: '#94a3b8', marginTop: 40, fontSize: 15, fontWeight: '500' },
  
  exportCard: { backgroundColor: '#ffffff', padding: 24, borderRadius: 16, borderWidth: 1, borderColor: '#e2e8f0' },
  exportTitle: { fontSize: 18, fontWeight: '800', color: '#0f172a', marginBottom: 8 },
  exportSubtitle: { fontSize: 14, color: '#64748b', marginBottom: 24 },
  inputGroup: { marginBottom: 16 },
  label: { fontSize: 12, fontWeight: '800', color: '#334155', marginBottom: 8, textTransform: 'uppercase' },
  input: { borderWidth: 1, borderColor: '#cbd5e1', borderRadius: 12, paddingHorizontal: 14, paddingVertical: 12, fontSize: 15, backgroundColor: '#f8fafc', color: '#0f172a' },
  exportBtn: { backgroundColor: '#2563eb', paddingVertical: 16, borderRadius: 12, alignItems: 'center', marginTop: 12 },
  disabledBtn: { opacity: 0.6 },
  exportBtnText: { color: '#ffffff', fontWeight: '800', fontSize: 15 },

  modalOverlay: { flex: 1, backgroundColor: 'rgba(15, 23, 42, 0.7)', justifyContent: 'center', padding: 20 },
  modalContent: { backgroundColor: '#ffffff', borderRadius: 24, padding: 24 },
  modalTitle: { fontSize: 20, fontWeight: '800', color: '#0f172a', marginBottom: 6 },
  modalSub: { fontSize: 14, color: '#64748b', marginBottom: 24 },

  searchContainer: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#ffffff', borderRadius: 12, borderWidth: 1, borderColor: '#cbd5e1', marginBottom: 16, height: 48 },
  teamSearchInput: { flex: 1, height: '100%', paddingHorizontal: 12, fontSize: 15, color: '#0f172a' },
  teamTabsRow: { flexDirection: 'row', marginBottom: 16, borderBottomWidth: 1, borderBottomColor: '#e2e8f0' },
  teamTabBtn: { flex: 1, paddingVertical: 12, alignItems: 'center', borderBottomWidth: 2, borderBottomColor: 'transparent' },
  teamTabBtnActive: { borderBottomColor: '#2563eb' },
  teamTabText: { fontSize: 13, fontWeight: '600', color: '#64748b' },
  teamTabTextActive: { color: '#2563eb', fontWeight: '800' },
});
