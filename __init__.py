from qgis.core import (
    Qgis,
    QgsProject,
    QgsFeatureRequest,
    QgsDataSourceUri,
    QgsProviderRegistry,
    QgsMessageLog
)
from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QDesktopServices
from qgis.PyQt.QtCore import QUrl
from qgis.PyQt.QtWidgets import (
    QAction,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
)
from qgis.PyQt.QtCore import QSettings

def classFactory(iface):
    return MinimalPlugin(iface)


class MinimalPlugin:

    def __init__(self, iface):
        self.iface = iface

    def initGui(self):
        self.action = QAction(
            text="Modell Dokumentation", 
            parent=self.iface.mainWindow()
        )
        self.action.triggered.connect(self.run)
        self.iface.addToolBarIcon(self.action)

        # Add a settings entry to the Plugins menu
        self.settings_action = QAction(
            "Settings",
            self.iface.mainWindow()
        )
        self.iface.addPluginToMenu(
            "docButton",
            self.settings_action
        )
        self.settings_action.triggered.connect(self.configure)

    def configure(self):
        # create settings object
        settings = QSettings()

        # get saved connection names
        provider_metadata = QgsProviderRegistry.instance().providerMetadata("postgres")
        conn_names = sorted(provider_metadata.connections().keys())

        # create a dialog object 
        dialog = QDialog(self.iface.mainWindow())
        dialog.setWindowTitle("Settings")

        # let user select one of the connections for use with plugin
        combo = QComboBox(dialog)
        combo.addItems(conn_names)

        # Load current setting
        current_name = settings.value(
            "docButton/postgres_connection", type=str
        )
        index = combo.findText(current_name)
        if index >= 0:
            combo.setCurrentIndex(index)

        # add ok and cancel buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=dialog
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)

        # create layout for GUI elements
        layout = QFormLayout(dialog)
        layout.addRow("PostgreSQL Datenbankverbindung", combo)
        layout.addRow(buttons)

        # Save the selection if the user clicks OK
        if dialog.exec():
            settings.setValue(
                "docButton/postgres_connection",
                combo.currentText()
            )


    def unload(self):
        self.iface.removeToolBarIcon(self.action)
        del self.action

    def run(self):
        # create settings object to access plugin settings through
        settings = QSettings()

        # Get selected layer to read data source from 
        activeLayer: QgsVectorLayer = self.iface.activeLayer() 
        
        if activeLayer is None:
            QgsMessageLog.logMessage(
                """
                No Layer selected. Please select a layer that belongs to the database
                model you'd like to view the documentation of.
                """,
                "docButton",
                Qgis.MessageLevel.Info
            )
            return

        # Get meta_attrs uri from active layer
        try: 
            uri: QgsDataSourceUri = QgsDataSourceUri(activeLayer.source())
        except:
            QgsMessageLog.logMessage(
                "Unable to find selected layer's data source.",
                "docButton",
                Qgis.MessageLevel.Info
            )
            return

        uri.setTable('t_ili2db_meta_attrs') # re-target uri to interlis metadata table holding model info    

        # configure data provider interface
        metadata = QgsProviderRegistry.instance().providerMetadata('postgres')
        conn = settings.value("docButton/postgres_connection", type=str)

        # check if setting was empty () 
        if conn is None or conn == '':
            # Warning ribbon
            self.iface.messageBar().pushMessage(
                "docButton",
                """
                No database connection setting found. Please configure which database connection to use in the plugin settings: Plugins > docButton."
                """,
                level=Qgis.MessageLevel.Warning,
                duration=0
            )
            return

        connection = metadata.createConnection(
            settings.value("docButton/postgres_connection", type=str)
        ) 

        # Query the data provider for docURL
        sql = f"SELECT attr_value FROM {uri.schema()}.{uri.table()} WHERE attr_name = \'docURL\';"
        queryResults = connection.executeSql(sql)
        docURL = queryResults[0][0]

        # Open URL in default web browser
        QDesktopServices.openUrl(
            QUrl(docURL)
        )