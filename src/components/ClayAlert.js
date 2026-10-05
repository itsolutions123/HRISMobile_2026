import React from 'react';
import { Modal, View, Text, TouchableOpacity, StyleSheet } from 'react-native';

export default function ClayAlert({ visible, title, message, onClose }) {
  return (
    <Modal transparent={true} visible={visible} animationType="fade">
      <View style={styles.overlay}>
        <View style={styles.clayBox}>
          <Text style={styles.title}>{title}</Text>
          <Text style={styles.message}>{message}</Text>
          
          <TouchableOpacity style={styles.clayButton} onPress={onClose} activeOpacity={0.7}>
            <Text style={styles.buttonText}>OK</Text>
          </TouchableOpacity>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(15, 23, 42, 0.4)', // Solid dim background instead of blur
  },
  clayBox: {
    width: '80%',
    backgroundColor: '#f1f5f9', // Soft solid color
    borderRadius: 32, // Extra rounded for clay look
    paddingTop: 24,
    paddingHorizontal: 20,
    paddingBottom: 20,
    alignItems: 'center',
    // Claymorphism top-left highlight and bottom-right shadow effect
    borderTopWidth: 2,
    borderLeftWidth: 2,
    borderTopColor: '#ffffff',
    borderLeftColor: '#ffffff',
    shadowColor: '#94a3b8',
    shadowOffset: { width: 8, height: 12 },
    shadowOpacity: 0.6,
    shadowRadius: 16,
    elevation: 10,
  },
  title: {
    fontSize: 19,
    fontWeight: '800',
    color: '#334155',
    marginBottom: 10,
    textAlign: 'center',
  },
  message: {
    fontSize: 15,
    color: '#475569',
    textAlign: 'center',
    marginBottom: 24,
    lineHeight: 22,
    fontWeight: '500',
  },
  clayButton: {
    width: '100%',
    paddingVertical: 14,
    alignItems: 'center',
    backgroundColor: '#e0e7ff',
    borderRadius: 20,
    borderTopWidth: 2,
    borderLeftWidth: 2,
    borderTopColor: '#ffffff',
    borderLeftColor: '#ffffff',
    shadowColor: '#94a3b8',
    shadowOffset: { width: 4, height: 6 },
    shadowOpacity: 0.4,
    shadowRadius: 8,
    elevation: 4,
  },
  buttonText: {
    color: '#4f46e5',
    fontSize: 17,
    fontWeight: '700',
  },
});
