import React, { useState, useEffect, useContext } from 'react';
import { View, Text, StyleSheet, FlatList, TouchableOpacity, ActivityIndicator, Alert, RefreshControl, TextInput, Linking } from 'react-native';
import { AuthContext } from '../context/AuthContext';

export default function ManagerScreen() {
  const { user, API_BASE_URL } = useContext(AuthContext);
  const [activeTab, setActiveTab] = useState('revisions'); // 'revisions', 'team', 'groups', 'export'
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const [revisions, setRevisions] = useState([]);
  const [team, setTeam] = useState([]);
  const [groups, setGroups] = useState([]);

  // Date range states for Export UI
  const [startDate, setStartDate] = useState(new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]);
  const [endDate, setEndDate] = useState(new Date().toISOString().split('T')[0]);
  const [exporting, setExporting] = useState(false);

  const fetchData = async () => {
    if (activeTab === 'export') {
      setLoading(false);
      setRefreshing(false);
      return;
    }

    try {
      if (activeTab === 'revisions') {
        const res = await fetch(`${API_BASE_URL}/api/manager/revisions`);
        if (res.ok) {
          const data = await res.json();
          setRevisions(data);
        }
      } else if (activeTab === 'team') {
        const res = await fetch(`${API_BASE_URL}/api/manager/team`);
        if (res.ok) {
          const data = await res.json();
          setTeam(data);
        }
      } else if (activeTab === 'groups') {
        const res = await fetch(`${API_BASE_URL}/api/manager/groups`);
        if (res.ok) {
          const data = await res.json();
          setGroups(data);
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
    setLoading(true);
    fetchData();
  }, [activeTab]);

  const onRefresh = () => {
    setRefreshing(true);
    fetchData();
  };

  const handleRevisionAction = async (revisionId, action) => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/manager/revisions/${revisionId}/action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action }),
      });
      if (res.ok) {
        Alert.alert('Success', `Revision ${action.toLowerCase()} successfully.`);
        fetchData();
      } else {
        const err = await res.json();
        Alert.alert('Error', err.detail || 'Failed to process request');
      }
    } catch (err) {
      Alert.alert('Error', 'Network or server error');
    }
  };

  const handleExportTimesheet = async () => {
    if (!startDate || !endDate) {
      Alert.alert('Validation Error', 'Please select both start and end dates.');
      return;
    }
    setExporting(true);
    try {
      const exportUrl = `${API_BASE_URL}/api/dtr/export?start_date=${startDate}&end_date=${endDate}`;
      const supported = await Linking.canOpenURL(exportUrl);
      if (supported) {
        await Linking.openURL(exportUrl);
      } else {
        Alert.alert('Error', `Cannot open download URL: ${exportUrl}`);
      }
    } catch (err) {
      Alert.alert('Export Error', 'Failed to trigger file download.');
    } finally {
      setExporting(false);
    }
  };

  const renderRevisionItem = ({ item }) => (
    <View style={styles.card}>
      <View style={styles.cardHeader}>
        <Text style={styles.cardTitle}>{item.employee_name} ({item.employee_id})</Text>
        <Text style={styles.pendingBadge}>{item.status}</Text>
      </View>
      <Text style={styles.cardDetail}>Type: <Text style={styles.boldText}>{item.requested_punch_type}</Text></Text>
      <Text style={styles.cardDetail}>Requested Time: {new Date(item.requested_timestamp).toLocaleString()}</Text>
      <Text style={styles.cardDetail}>Reason: {item.reason}</Text>

      <View style={styles.actionRow}>
        <TouchableOpacity
          style={[styles.actionBtn, styles.approveBtn]}
          onPress={() => handleRevisionAction(item.id, 'APPROVED')}
        >
          <Text style={styles.btnText}>Approve</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.actionBtn, styles.rejectBtn]}
          onPress={() => handleRevisionAction(item.id, 'REJECTED')}
        >
          <Text style={styles.btnText}>Reject</Text>
        </TouchableOpacity>
      </View>
    </View>
  );

  const renderTeamItem = ({ item }) => (
    <View style={styles.card}>
      <Text style={styles.cardTitle}>{item.name}</Text>
      <Text style={styles.cardDetail}>ID: {item.employee_id} | Role: {item.role}</Text>
      <Text style={styles.cardDetail}>Position: {item.position || 'N/A'}</Text>
      <Text style={styles.cardDetail}>Department: {item.department || 'N/A'}</Text>
    </View>
  );

  const renderGroupItem = ({ item }) => (
    <View style={styles.card}>
      <View style={styles.cardHeader}>
        <Text style={styles.cardTitle}>{item.name}</Text>
        <Text style={styles.countBadge}>{item.assigned_count} Assigned</Text>
      </View>
      <Text style={styles.cardDetail}>{item.description || 'No description'}</Text>
    </View>
  );

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

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Manager Hub</Text>

      {/* Navigation Tabs */}
      <View style={styles.tabContainer}>
        <TouchableOpacity
          style={[styles.tab, activeTab === 'revisions' && styles.activeTab]}
          onPress={() => setActiveTab('revisions')}
        >
          <Text style={[styles.tabText, activeTab === 'revisions' && styles.activeTabText]}>Revisions</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.tab, activeTab === 'team' && styles.activeTab]}
          onPress={() => setActiveTab('team')}
        >
          <Text style={[styles.tabText, activeTab === 'team' && styles.activeTabText]}>Team</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.tab, activeTab === 'groups' && styles.activeTab]}
          onPress={() => setActiveTab('groups')}
        >
          <Text style={[styles.tabText, activeTab === 'groups' && styles.activeTabText]}>Groups</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.tab, activeTab === 'export' && styles.activeTab]}
          onPress={() => setActiveTab('export')}
        >
          <Text style={[styles.tabText, activeTab === 'export' && styles.activeTabText]}>Export</Text>
        </TouchableOpacity>
      </View>

      {loading ? (
        <ActivityIndicator size="large" color="#2563eb" style={{ marginTop: 20 }} />
      ) : activeTab === 'export' ? (
        renderExportView()
      ) : (
        <FlatList
          data={activeTab === 'revisions' ? revisions : activeTab === 'team' ? team : groups}
          keyExtractor={(item) => item.id ? item.id.toString() : item.employee_id}
          renderItem={activeTab === 'revisions' ? renderRevisionItem : activeTab === 'team' ? renderTeamItem : renderGroupItem}
          contentContainerStyle={{ paddingBottom: 20 }}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
          ListEmptyComponent={
            <Text style={styles.emptyText}>
              {activeTab === 'revisions' ? 'No pending DTR revisions.' : activeTab === 'team' ? 'No team members found.' : 'No schedule groups available.'}
            </Text>
          }
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 16, backgroundColor: '#f8fafc' },
  title: { fontSize: 22, fontWeight: 'bold', color: '#0f172a', marginBottom: 12 },
  tabContainer: { flexDirection: 'row', marginBottom: 16, backgroundColor: '#e2e8f0', borderRadius: 8, padding: 4 },
  tab: { flex: 1, paddingVertical: 8, alignItems: 'center', borderRadius: 6 },
  activeTab: { backgroundColor: '#ffffff', elevation: 2 },
  tabText: { fontSize: 12, fontWeight: '600', color: '#64748b' },
  activeTabText: { color: '#2563eb' },
  card: { backgroundColor: '#ffffff', padding: 14, borderRadius: 10, marginBottom: 12, borderWidth: 1, borderColor: '#cbd5e1' },
  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 },
  cardTitle: { fontWeight: 'bold', fontSize: 16, color: '#1e293b' },
  cardDetail: { fontSize: 13, color: '#475569', marginTop: 2 },
  boldText: { fontWeight: 'bold', color: '#0f172a' },
  pendingBadge: { backgroundColor: '#fef3c7', color: '#d97706', paddingHorizontal: 8, paddingVertical: 2, borderRadius: 4, fontWeight: 'bold', fontSize: 11 },
  countBadge: { backgroundColor: '#e0f2fe', color: '#0369a1', paddingHorizontal: 8, paddingVertical: 2, borderRadius: 4, fontWeight: 'bold', fontSize: 11 },
  actionRow: { flexDirection: 'row', marginTop: 12, gap: 10 },
  actionBtn: { flex: 1, paddingVertical: 8, borderRadius: 6, alignItems: 'center' },
  approveBtn: { backgroundColor: '#16a34a' },
  rejectBtn: { backgroundColor: '#dc2626' },
  btnText: { color: '#ffffff', fontWeight: 'bold', fontSize: 13 },
  emptyText: { textAlign: 'center', color: '#94a3b8', marginTop: 40, fontSize: 14 },
  exportCard: { backgroundColor: '#ffffff', padding: 16, borderRadius: 10, borderWidth: 1, borderColor: '#cbd5e1' },
  exportTitle: { fontSize: 18, fontWeight: 'bold', color: '#0f172a', marginBottom: 4 },
  exportSubtitle: { fontSize: 13, color: '#64748b', marginBottom: 16 },
  inputGroup: { marginBottom: 14 },
  label: { fontSize: 13, fontWeight: '600', color: '#334155', marginBottom: 4 },
  input: { borderWidth: 1, borderColor: '#cbd5e1', borderRadius: 6, paddingHorizontal: 10, paddingVertical: 8, fontSize: 14, backgroundColor: '#f8fafc', color: '#0f172a' },
  exportBtn: { backgroundColor: '#2563eb', paddingVertical: 12, borderRadius: 8, alignItems: 'center', marginTop: 8 },
  disabledBtn: { opacity: 0.6 },
  exportBtnText: { color: '#ffffff', fontWeight: 'bold', fontSize: 14 },
});
