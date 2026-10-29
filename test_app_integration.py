"""
UI Integration Tests - Tests for the new page rendering functions in app.py.

These tests verify that the new integrated pages can be imported and
their rendering functions don't have syntax/import errors.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, PropertyMock
import streamlit as st

# Import the app module to test page functions
import app


class MockSessionState:
    """Mock session state that supports both dict and attribute access."""
    def __init__(self, **kwargs):
        self._data = kwargs
    
    def __getattr__(self, name):
        if name in self._data:
            return self._data[name]
        # Return a mock for any missing attribute to avoid AttributeError
        return Mock()
    
    def __getitem__(self, name):
        return self._data.get(name, Mock())
    
    def __setitem__(self, name, value):
        self._data[name] = value
    
    def get(self, name, default=None):
        return self._data.get(name, default)
    
    def __contains__(self, name):
        return name in self._data


class TestAppIntegration:
    """Tests for app.py page rendering functions."""

    def test_render_device_info_no_device(self):
        """Test render_device_info handles no device gracefully."""
        with patch('app.st') as mock_st:
            mock_st.session_state = MockSessionState(
                demo_mode=False,
                connection_status='disconnected',
                device_info={
                    'manufacturer': 'Unknown',
                    'model': 'Unknown',
                    'android_version': 'Unknown',
                    'storage': 'Unknown',
                    'adb_status': 'Not connected',
                },
                adb_manager=Mock(connection_state=app.ADBState.NO_DEVICE),
            )
            mock_st.markdown = Mock()
            mock_st.info = Mock()
            mock_st.button = Mock(return_value=False)
            mock_st.spinner = Mock(return_value=Mock(__enter__=Mock(return_value=None), __exit__=Mock(return_value=None)))
            mock_st.success = Mock()
            mock_st.error = Mock()
            mock_st.rerun = Mock()
            mock_st.expander = Mock(return_value=Mock(__enter__=Mock(return_value=None), __exit__=Mock(return_value=None)))
            
            app.render_device_info()
            
            # Should show "No Device Connected" message
            assert mock_st.markdown.called

    def test_render_apps_no_device(self):
        """Test render_apps handles no device gracefully."""
        with patch('app.st') as mock_st:
            mock_st.session_state = MockSessionState(
                demo_mode=False,
                adb_manager=Mock(connection_state=app.ADBState.NO_DEVICE),
            )
            mock_st.markdown = Mock()
            mock_st.info = Mock()
            mock_st.button = Mock(return_value=False)
            mock_st.columns = Mock(return_value=[Mock(), Mock(), Mock()])
            mock_st.selectbox = Mock(return_value="All")
            mock_st.caption = Mock()
            mock_st.container = Mock(return_value=Mock(__enter__=Mock(return_value=None), __exit__=Mock(return_value=None)))
            mock_st.expander = Mock(return_value=Mock(__enter__=Mock(return_value=None), __exit__=Mock(return_value=None)))
            mock_st.code = Mock()
            mock_st.warning = Mock()
            mock_st.metric = Mock()
            
            app.render_apps()
            
            assert mock_st.markdown.called

    def test_render_recommendations_no_device(self):
        """Test render_recommendations handles no device gracefully."""
        with patch('app.st') as mock_st:
            mock_st.session_state = MockSessionState(
                demo_mode=False,
                adb_manager=Mock(connection_state=app.ADBState.NO_DEVICE),
                recommendations=[],
            )
            mock_st.markdown = Mock()
            mock_st.info = Mock()
            mock_st.button = Mock(return_value=False)
            mock_st.columns = Mock(return_value=[Mock(), Mock()])
            mock_st.selectbox = Mock(return_value="All")
            
            app.render_recommendations()
            
            assert mock_st.markdown.called

    def test_render_performance_no_device(self):
        """Test render_performance handles no device gracefully."""
        with patch('app.st') as mock_st:
            mock_st.session_state = MockSessionState(
                demo_mode=False,
                adb_manager=Mock(connection_state=app.ADBState.NO_DEVICE),
                performance_metrics={},
            )
            mock_st.markdown = Mock()
            mock_st.info = Mock()
            mock_st.button = Mock(return_value=False)
            mock_st.columns = Mock(return_value=[Mock(), Mock()])
            
            app.render_performance()
            
            assert mock_st.markdown.called

    def test_render_backups_no_device(self):
        """Test render_backups handles no device gracefully."""
        with patch('app.st') as mock_st:
            mock_st.session_state = MockSessionState(
                demo_mode=False,
                adb_manager=Mock(connection_state=app.ADBState.NO_DEVICE),
            )
            mock_st.markdown = Mock()
            mock_st.info = Mock()
            mock_st.button = Mock(return_value=False)
            mock_st.selectbox = Mock(return_value=app.BackupType.FULL)
            mock_st.text_input = Mock(return_value="")
            mock_st.expander = Mock(return_value=Mock(__enter__=Mock(return_value=None), __exit__=Mock(return_value=None)))
            mock_st.columns = Mock(return_value=[Mock(), Mock(), Mock()])
            mock_st.success = Mock()
            mock_st.error = Mock()
            
            app.render_backups()
            
            assert mock_st.markdown.called

    def test_render_activity_log_no_device(self):
        """Test render_activity_log handles no device gracefully."""
        with patch('app.st') as mock_st:
            mock_st.session_state = MockSessionState(
                demo_mode=False,
                adb_manager=Mock(connection_state=app.ADBState.NO_DEVICE),
            )
            mock_st.markdown = Mock()
            mock_st.info = Mock()
            mock_st.selectbox = Mock(return_value="All Devices")
            mock_st.columns = Mock(return_value=[Mock(), Mock(), Mock(), Mock(), Mock()])
            mock_st.metric = Mock()
            mock_st.container = Mock(return_value=Mock(__enter__=Mock(return_value=None), __exit__=Mock(return_value=None)))
            mock_st.expander = Mock(return_value=Mock(__enter__=Mock(return_value=None), __exit__=Mock(return_value=None)))
            mock_st.button = Mock(return_value=False)
            mock_st.warning = Mock()
            
            app.render_activity_log()
            
            assert mock_st.markdown.called

    def test_initialize_modules(self):
        """Test _initialize_modules creates all module instances."""
        with patch('app.st') as mock_st:
            mock_adb_manager = Mock()
            mock_st.session_state = MockSessionState(
                adb_manager=mock_adb_manager,
                device_identifier=None,
                diagnostics_engine=None,
                package_inventory=None,
                package_classifier=None,
                recommendation_engine=None,
                performance_monitor=None,
                backup_manager=None,
                action_history=None,
                action_engine=None,
            )
            
            # Mock all factory functions using their actual names in app module
            with patch('app.create_device_identifier') as mock_di, \
                 patch('app.create_diagnostics_engine') as mock_de, \
                 patch('app.create_package_inventory') as mock_pi, \
                 patch('app.create_package_classifier') as mock_pc, \
                 patch('app.create_recommendation_engine') as mock_re, \
                 patch('app.create_performance_monitor') as mock_pm, \
                 patch('app.create_backup_manager') as mock_bm, \
                 patch('app.create_action_history') as mock_ah, \
                 patch('app.create_action_engine') as mock_ae:
                
                app._initialize_modules()
                
                # Verify all factories were called
                mock_di.assert_called_once_with(mock_adb_manager)
                mock_de.assert_called_once_with(mock_adb_manager)
                mock_pi.assert_called_once_with(mock_adb_manager)
                mock_pc.assert_called_once()
                mock_re.assert_called_once_with(mock_adb_manager)
                mock_pm.assert_called_once_with(mock_adb_manager)
                mock_bm.assert_called_once_with(mock_adb_manager)
                mock_ah.assert_called_once()
                mock_ae.assert_called_once_with(mock_adb_manager)

    def test_render_device_info_demo_mode(self):
        """Test render_device_info in demo mode shows info box."""
        with patch('app.st') as mock_st:
            mock_st.session_state = MockSessionState(
                demo_mode=True,
                connection_status='disconnected',
                device_info={
                    'manufacturer': 'Unknown',
                    'model': 'Unknown',
                    'android_version': 'Unknown',
                    'storage': 'Unknown',
                    'adb_status': 'Not connected',
                },
            )
            mock_st.markdown = Mock()
            mock_st.info = Mock()
            mock_st.button = Mock(return_value=False)
            
            app.render_device_info()
            
            # Should show demo mode info box
            mock_st.markdown.assert_called()

    def test_render_apps_demo_mode(self):
        """Test render_apps in demo mode shows info box."""
        with patch('app.st') as mock_st:
            mock_st.session_state = MockSessionState(
                demo_mode=True,
            )
            mock_st.markdown = Mock()
            mock_st.info = Mock()
            
            app.render_apps()
            
            mock_st.markdown.assert_called()

    def test_render_recommendations_demo_mode(self):
        """Test render_recommendations in demo mode shows info box."""
        with patch('app.st') as mock_st:
            mock_st.session_state = MockSessionState(
                demo_mode=True,
            )
            mock_st.markdown = Mock()
            mock_st.info = Mock()
            
            app.render_recommendations()
            
            mock_st.markdown.assert_called()

    def test_render_performance_demo_mode(self):
        """Test render_performance in demo mode shows info box."""
        with patch('app.st') as mock_st:
            mock_st.session_state = MockSessionState(
                demo_mode=True,
            )
            mock_st.markdown = Mock()
            mock_st.info = Mock()
            
            app.render_performance()
            
            mock_st.markdown.assert_called()

    def test_render_backups_demo_mode(self):
        """Test render_backups in demo mode shows info box."""
        with patch('app.st') as mock_st:
            mock_st.session_state = MockSessionState(
                demo_mode=True,
            )
            mock_st.markdown = Mock()
            mock_st.info = Mock()
            
            app.render_backups()
            
            mock_st.markdown.assert_called()

    def test_render_activity_log_demo_mode(self):
        """Test render_activity_log in demo mode shows info box."""
        with patch('app.st') as mock_st:
            mock_st.session_state = MockSessionState(
                demo_mode=True,
            )
            mock_st.markdown = Mock()
            mock_st.info = Mock()
            
            app.render_activity_log()
            
            mock_st.markdown.assert_called()

    def test_app_imports_all_modules(self):
        """Test that all required modules can be imported."""
        # This test passes if imports at top of app.py work
        assert hasattr(app, 'DeviceIdentifier')
        assert hasattr(app, 'DiagnosticsEngine')
        assert hasattr(app, 'PackageInventory')
        assert hasattr(app, 'PackageClassifier')
        assert hasattr(app, 'RecommendationEngine')
        assert hasattr(app, 'PerformanceMonitor')
        assert hasattr(app, 'BackupManager')
        assert hasattr(app, 'ActionHistory')
        assert hasattr(app, 'ActionEngine')


class TestPageRouting:
    """Tests for page routing in main()."""

    def test_main_routes_home(self):
        """Test main routes to home page."""
        with patch('app.page', '🏠 Home'), \
             patch('app.render_home') as mock_home, \
             patch('app.st.markdown'):
            app.main()
            mock_home.assert_called_once()

    def test_main_routes_connect(self):
        """Test main routes to connect page."""
        with patch('app.page', '🔌 Connect Your TV'), \
             patch('app.render_connect') as mock_connect, \
             patch('app.st.markdown'):
            app.main()
            mock_connect.assert_called_once()

    def test_main_routes_diagnostics(self):
        """Test main routes to diagnostics page."""
        with patch('app.page', '🔍 Device Diagnostics'), \
             patch('app.render_diagnostics') as mock_diag, \
             patch('app.st.markdown'):
            app.main()
            mock_diag.assert_called_once()

    def test_main_routes_demo_diagnostics(self):
        """Test main routes to demo diagnostics page."""
        with patch('app.page', '🧪 Demo Diagnostics'), \
             patch('app.render_demo_diagnostics') as mock_demo, \
             patch('app.st.markdown'):
            app.main()
            mock_demo.assert_called_once()

    def test_main_routes_apps(self):
        """Test main routes to apps page."""
        with patch('app.page', '📱 Installed Apps'), \
             patch('app.render_apps') as mock_apps, \
             patch('app.st.markdown'):
            app.main()
            mock_apps.assert_called_once()

    def test_main_routes_recommendations(self):
        """Test main routes to recommendations page."""
        with patch('app.page', '✨ Recommendations'), \
             patch('app.render_recommendations') as mock_rec, \
             patch('app.st.markdown'):
            app.main()
            mock_rec.assert_called_once()

    def test_main_routes_performance(self):
        """Test main routes to performance page."""
        with patch('app.page', '📊 Performance'), \
             patch('app.render_performance') as mock_perf, \
             patch('app.st.markdown'):
            app.main()
            mock_perf.assert_called_once()

    def test_main_routes_backups(self):
        """Test main routes to backups page."""
        with patch('app.page', '💾 Backups & Recovery'), \
             patch('app.render_backups') as mock_backups, \
             patch('app.st.markdown'):
            app.main()
            mock_backups.assert_called_once()

    def test_main_routes_activity_log(self):
        """Test main routes to activity log page."""
        with patch('app.page', '📜 Activity Log'), \
             patch('app.render_activity_log') as mock_log, \
             patch('app.st.markdown'):
            app.main()
            mock_log.assert_called_once()

    def test_main_routes_improvements(self):
        """Test main routes to improvements page."""
        with patch('app.page', '✨ Supported Improvements'), \
             patch('app.render_improvements') as mock_imp, \
             patch('app.st.markdown'):
            app.main()
            mock_imp.assert_called_once()

    def test_main_routes_safety(self):
        """Test main routes to safety page."""
        with patch('app.page', '🛡️ Safety & Recovery'), \
             patch('app.render_safety') as mock_safety, \
             patch('app.st.markdown'):
            app.main()
            mock_safety.assert_called_once()


class TestSessionStateInitialization:
    """Tests for new session state variables."""

    def test_session_state_has_new_module_keys(self):
        """Test that new module session state keys exist."""
        # These are initialized in the app.py module level
        expected_keys = [
            'device_identifier',
            'diagnostics_engine',
            'package_inventory',
            'package_classifier',
            'recommendation_engine',
            'performance_monitor',
            'backup_manager',
            'action_history',
            'action_engine',
            'diagnostic_result',
            'package_assessments',
            'recommendations',
            'performance_metrics',
            'selected_backup_id',
            'pending_action_id',
        ]
        
        # We can't easily test module-level init without running streamlit,
        # but we can verify the keys are referenced in the code
        import inspect
        source = inspect.getsource(app)
        
        for key in expected_keys:
            assert f'"{key}"' in source or f"'{key}'" in source, f"Missing session state key: {key}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])