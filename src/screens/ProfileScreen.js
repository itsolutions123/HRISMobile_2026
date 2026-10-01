import React, { useContext } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ScrollView, Alert } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { AuthContext } from '../context/AuthContext';

export default function ProfileScreen() {
  const { user, logout } = useContext(AuthContext);

  const handleLogout = () => {
    Alert.alert(
      "Confirm Logout",
      "Are you sure you want to log out of your account?",
      [
        { text: "Cancel", style: "cancel" },
        { text: "Logout", style: "destructive", onPress: logout }
      ]
    );
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* Top Profile Card */}
      <View style={styles.profileCard}>
        <View style={styles.profileHeader}>
          <View style={styles.logoPlaceholder}>
            <Ionicons name="business" size={28} color="#2563eb" />
          </View>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>{user?.name ? user.name.charAt(0).toUpperCase() : 'U'}</Text>
          </View>
        </View>
        <Text style={styles.employeeName}>{user?.name || 'Employee Name'}</Text>
        <Text style={styles.employeeTitle}>{user?.position || 'Staff'} • {user?.department || 'General'}</Text>
      </View>

      {/* Leave Section */}
      <Text style={styles.sectionTitle}>LEAVE</Text>
      <View style={styles.leaveRow}>
        <View style={styles.leaveBox}>
          <Text style={styles.leaveCount}>0</Text>
          <Text style={styles.leaveLabel}>PAID</Text>
        </View>
        <View style={styles.leaveBox}>
          <Text style={styles.leaveCount}>0</Text>
          <Text style={styles.leaveLabel}>VACATION</Text>
        </View>
        <View style={styles.leaveBox}>
          <Text style={styles.leaveCount}>0</Text>
          <Text style={styles.leaveLabel}>OFFSET</Text>
        </View>
      </View>

      {/* Form Submissions */}
      <Text style={styles.sectionTitle}>FORM SUBMISSIONS</Text>
      <View style={styles.listCard}>
        <TouchableOpacity style={styles.listItem} onPress={() => alert('My Submissions coming soon')}>
          <Text style={styles.listItemText}>My Submissions</Text>
          <Ionicons name="chevron-forward" size={20} color="#cbd5e1" />
        </TouchableOpacity>
      </View>

      {/* More Section */}
      <Text style={styles.sectionTitle}>MORE</Text>
      <View style={styles.listCard}>
        <TouchableOpacity style={styles.listItem} onPress={() => alert('Personal Information coming soon')}>
          <Text style={styles.listItemText}>Personal Information</Text>
          <Ionicons name="chevron-forward" size={20} color="#cbd5e1" />
        </TouchableOpacity>
        <TouchableOpacity style={styles.listItem} onPress={() => alert('Settings coming soon')}>
          <Text style={styles.listItemText}>Settings</Text>
          <Ionicons name="chevron-forward" size={20} color="#cbd5e1" />
        </TouchableOpacity>
        <TouchableOpacity style={[styles.listItem, { borderBottomWidth: 0 }]} onPress={handleLogout}>
          <Text style={[styles.listItemText, { color: '#ef4444' }]}>Logout</Text>
          <Ionicons name="log-out-outline" size={20} color="#ef4444" />
        </TouchableOpacity>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f8fafc' },
  content: { padding: 20, paddingTop: 40, paddingBottom: 40 },
  profileCard: { backgroundColor: '#ffffff', borderRadius: 16, padding: 24, marginBottom: 32, borderWidth: 1, borderColor: '#e2e8f0', shadowColor: '#000', shadowOpacity: 0.05, shadowRadius: 8, elevation: 3 },
  profileHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 },
  logoPlaceholder: { width: 50, height: 50, borderRadius: 12, backgroundColor: '#eff6ff', justifyContent: 'center', alignItems: 'center' },
  avatar: { width: 64, height: 64, borderRadius: 16, backgroundColor: '#2563eb', justifyContent: 'center', alignItems: 'center' },
  avatarText: { color: '#ffffff', fontSize: 28, fontWeight: '800' },
  employeeName: { fontSize: 20, fontWeight: '800', color: '#0f172a', marginBottom: 4 },
  employeeTitle: { fontSize: 13, color: '#64748b', fontWeight: '600', textTransform: 'uppercase', letterSpacing: 0.5 },
  
  sectionTitle: { fontSize: 13, fontWeight: '800', color: '#64748b', marginBottom: 12, letterSpacing: 0.5 },
  leaveRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 32 },
  leaveBox: { flex: 1, backgroundColor: '#ffffff', borderRadius: 16, paddingVertical: 20, alignItems: 'center', marginHorizontal: 4, borderWidth: 1, borderColor: '#e2e8f0', shadowColor: '#000', shadowOpacity: 0.03, shadowRadius: 4, elevation: 2 },
  leaveCount: { fontSize: 24, fontWeight: '800', color: '#0f172a', marginBottom: 4 },
  leaveLabel: { fontSize: 10, fontWeight: '800', color: '#64748b', textTransform: 'uppercase' },
  
  listCard: { backgroundColor: '#ffffff', borderRadius: 16, marginBottom: 32, borderWidth: 1, borderColor: '#e2e8f0', overflow: 'hidden', shadowColor: '#000', shadowOpacity: 0.03, shadowRadius: 4, elevation: 2 },
  listItem: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: 18, borderBottomWidth: 1, borderBottomColor: '#f1f5f9' },
  listItemText: { fontSize: 15, fontWeight: '700', color: '#1e293b' },
});
