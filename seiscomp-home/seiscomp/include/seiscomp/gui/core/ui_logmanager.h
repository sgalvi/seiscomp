/********************************************************************************
** Form generated from reading UI file 'logmanager.ui'
**
** Created by: Qt User Interface Compiler version 5.15.13
**
** WARNING! All changes made in this file will be lost when recompiling UI file!
********************************************************************************/

#ifndef UI_LOGMANAGER_H
#define UI_LOGMANAGER_H

#include <QtCore/QVariant>
#include <QtWidgets/QAction>
#include <QtWidgets/QApplication>
#include <QtWidgets/QComboBox>
#include <QtWidgets/QHBoxLayout>
#include <QtWidgets/QHeaderView>
#include <QtWidgets/QLabel>
#include <QtWidgets/QLineEdit>
#include <QtWidgets/QMainWindow>
#include <QtWidgets/QPushButton>
#include <QtWidgets/QSpacerItem>
#include <QtWidgets/QTableView>
#include <QtWidgets/QToolBar>
#include <QtWidgets/QVBoxLayout>
#include <QtWidgets/QWidget>

QT_BEGIN_NAMESPACE

class Ui_LogManager
{
public:
    QAction *actionCopyCell;
    QAction *actionFilter;
    QAction *actionPause;
    QWidget *centralwidget;
    QAction *clear;
    QAction *settings;
    QAction *critical;
    QAction *error;
    QAction *warning;
    QAction *notice;
    QAction *info;
    QAction *debug;
    QAction *actionCopy;
    QVBoxLayout *vboxLayout;
    QTableView *tableView;
    QHBoxLayout *hboxLayout;
    QLabel *labelFilter;
    QComboBox *comboFilterSource;
    QLineEdit *editFilter;
    QSpacerItem *horizontalSpacer;
    QPushButton *pushButton;
    QToolBar *toolBar;

    void setupUi(QMainWindow *LogManager)
    {
        if (LogManager->objectName().isEmpty())
            LogManager->setObjectName(QString::fromUtf8("LogManager"));
        LogManager->resize(584, 513);
        actionCopyCell = new QAction(LogManager);
        actionCopyCell->setObjectName(QString::fromUtf8("actionCopyCell"));
        actionFilter = new QAction(LogManager);
        actionFilter->setObjectName(QString::fromUtf8("actionFilter"));
        actionPause = new QAction(LogManager);
        actionPause->setObjectName(QString::fromUtf8("actionPause"));
        actionPause->setCheckable(true);
        centralwidget = new QWidget(LogManager);
        centralwidget->setObjectName(QString::fromUtf8("centralwidget"));
        clear = new QAction(centralwidget);
        clear->setObjectName(QString::fromUtf8("clear"));
        QIcon icon;
        icon.addFile(QString::fromUtf8("../../../../../../../../../.designer/backup"), QSize(), QIcon::Normal, QIcon::Off);
        clear->setIcon(icon);
        settings = new QAction(centralwidget);
        settings->setObjectName(QString::fromUtf8("settings"));
        settings->setIcon(icon);
        critical = new QAction(centralwidget);
        critical->setObjectName(QString::fromUtf8("critical"));
        critical->setCheckable(true);
        critical->setChecked(false);
        error = new QAction(centralwidget);
        error->setObjectName(QString::fromUtf8("error"));
        error->setCheckable(true);
        error->setChecked(false);
        warning = new QAction(centralwidget);
        warning->setObjectName(QString::fromUtf8("warning"));
        warning->setCheckable(true);
        warning->setChecked(false);
        notice = new QAction(centralwidget);
        notice->setObjectName(QString::fromUtf8("notice"));
        notice->setCheckable(true);
        notice->setChecked(false);
        info = new QAction(centralwidget);
        info->setObjectName(QString::fromUtf8("info"));
        info->setCheckable(true);
        info->setChecked(false);
        debug = new QAction(centralwidget);
        debug->setObjectName(QString::fromUtf8("debug"));
        debug->setCheckable(true);
        debug->setChecked(false);
        actionCopy = new QAction(centralwidget);
        actionCopy->setObjectName(QString::fromUtf8("actionCopy"));
        vboxLayout = new QVBoxLayout(centralwidget);
        vboxLayout->setSpacing(6);
        vboxLayout->setObjectName(QString::fromUtf8("vboxLayout"));
        vboxLayout->setContentsMargins(9, 9, 9, 9);
        tableView = new QTableView(centralwidget);
        tableView->setObjectName(QString::fromUtf8("tableView"));
        tableView->setSortingEnabled(true);

        vboxLayout->addWidget(tableView);

        hboxLayout = new QHBoxLayout();
        hboxLayout->setSpacing(6);
        hboxLayout->setObjectName(QString::fromUtf8("hboxLayout"));
        hboxLayout->setContentsMargins(0, 0, 0, 0);
        labelFilter = new QLabel(centralwidget);
        labelFilter->setObjectName(QString::fromUtf8("labelFilter"));
        QSizePolicy sizePolicy(QSizePolicy::Maximum, QSizePolicy::Preferred);
        sizePolicy.setHorizontalStretch(0);
        sizePolicy.setVerticalStretch(0);
        sizePolicy.setHeightForWidth(labelFilter->sizePolicy().hasHeightForWidth());
        labelFilter->setSizePolicy(sizePolicy);

        hboxLayout->addWidget(labelFilter);

        comboFilterSource = new QComboBox(centralwidget);
        comboFilterSource->setObjectName(QString::fromUtf8("comboFilterSource"));
        QSizePolicy sizePolicy1(QSizePolicy::Maximum, QSizePolicy::Fixed);
        sizePolicy1.setHorizontalStretch(0);
        sizePolicy1.setVerticalStretch(0);
        sizePolicy1.setHeightForWidth(comboFilterSource->sizePolicy().hasHeightForWidth());
        comboFilterSource->setSizePolicy(sizePolicy1);

        hboxLayout->addWidget(comboFilterSource);

        editFilter = new QLineEdit(centralwidget);
        editFilter->setObjectName(QString::fromUtf8("editFilter"));
        QSizePolicy sizePolicy2(QSizePolicy::Expanding, QSizePolicy::Fixed);
        sizePolicy2.setHorizontalStretch(1);
        sizePolicy2.setVerticalStretch(0);
        sizePolicy2.setHeightForWidth(editFilter->sizePolicy().hasHeightForWidth());
        editFilter->setSizePolicy(sizePolicy2);
        editFilter->setMaximumSize(QSize(400, 16777215));

        hboxLayout->addWidget(editFilter);

        horizontalSpacer = new QSpacerItem(40, 0, QSizePolicy::Expanding, QSizePolicy::Minimum);

        hboxLayout->addItem(horizontalSpacer);

        pushButton = new QPushButton(centralwidget);
        pushButton->setObjectName(QString::fromUtf8("pushButton"));
        sizePolicy1.setHeightForWidth(pushButton->sizePolicy().hasHeightForWidth());
        pushButton->setSizePolicy(sizePolicy1);

        hboxLayout->addWidget(pushButton);


        vboxLayout->addLayout(hboxLayout);

        LogManager->setCentralWidget(centralwidget);
        toolBar = new QToolBar(LogManager);
        toolBar->setObjectName(QString::fromUtf8("toolBar"));
        toolBar->setIconSize(QSize(24, 24));
        LogManager->addToolBar(Qt::TopToolBarArea, toolBar);
        QWidget::setTabOrder(tableView, comboFilterSource);
        QWidget::setTabOrder(comboFilterSource, editFilter);
        QWidget::setTabOrder(editFilter, pushButton);

        retranslateUi(LogManager);
        QObject::connect(pushButton, SIGNAL(clicked()), LogManager, SLOT(close()));

        QMetaObject::connectSlotsByName(LogManager);
    } // setupUi

    void retranslateUi(QMainWindow *LogManager)
    {
        LogManager->setWindowTitle(QCoreApplication::translate("LogManager", "Log view", nullptr));
        actionCopyCell->setText(QCoreApplication::translate("LogManager", "Copy cell to clipboard", nullptr));
#if QT_CONFIG(tooltip)
        actionCopyCell->setToolTip(QCoreApplication::translate("LogManager", "Copy cell to clipboard", nullptr));
#endif // QT_CONFIG(tooltip)
        actionFilter->setText(QCoreApplication::translate("LogManager", "Filter", nullptr));
#if QT_CONFIG(tooltip)
        actionFilter->setToolTip(QCoreApplication::translate("LogManager", "Edit filter text", nullptr));
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(shortcut)
        actionFilter->setShortcut(QCoreApplication::translate("LogManager", "Ctrl+F", nullptr));
#endif // QT_CONFIG(shortcut)
        actionPause->setText(QCoreApplication::translate("LogManager", "Pause", nullptr));
#if QT_CONFIG(tooltip)
        actionPause->setToolTip(QCoreApplication::translate("LogManager", "Pauses feeding log messages into this view", nullptr));
#endif // QT_CONFIG(tooltip)
        clear->setText(QCoreApplication::translate("LogManager", "Clear", nullptr));
#if QT_CONFIG(tooltip)
        clear->setToolTip(QCoreApplication::translate("LogManager", "Clear log", nullptr));
#endif // QT_CONFIG(tooltip)
        settings->setText(QCoreApplication::translate("LogManager", "Settings", nullptr));
#if QT_CONFIG(tooltip)
        settings->setToolTip(QCoreApplication::translate("LogManager", "Show settings", nullptr));
#endif // QT_CONFIG(tooltip)
        critical->setText(QCoreApplication::translate("LogManager", "Critical", nullptr));
#if QT_CONFIG(tooltip)
        critical->setToolTip(QCoreApplication::translate("LogManager", "Show/hide critical messages", nullptr));
#endif // QT_CONFIG(tooltip)
        error->setText(QCoreApplication::translate("LogManager", "Error", nullptr));
#if QT_CONFIG(tooltip)
        error->setToolTip(QCoreApplication::translate("LogManager", "Show/hide error messages", nullptr));
#endif // QT_CONFIG(tooltip)
        warning->setText(QCoreApplication::translate("LogManager", "Warning", nullptr));
#if QT_CONFIG(tooltip)
        warning->setToolTip(QCoreApplication::translate("LogManager", "Show/hide warning messages", nullptr));
#endif // QT_CONFIG(tooltip)
        notice->setText(QCoreApplication::translate("LogManager", "Notice", nullptr));
#if QT_CONFIG(tooltip)
        notice->setToolTip(QCoreApplication::translate("LogManager", "Show/hide notice messages", nullptr));
#endif // QT_CONFIG(tooltip)
        info->setText(QCoreApplication::translate("LogManager", "Info", nullptr));
#if QT_CONFIG(tooltip)
        info->setToolTip(QCoreApplication::translate("LogManager", "Show/hide info messages", nullptr));
#endif // QT_CONFIG(tooltip)
        debug->setText(QCoreApplication::translate("LogManager", "Debug", nullptr));
#if QT_CONFIG(tooltip)
        debug->setToolTip(QCoreApplication::translate("LogManager", "Show/hide debug messages", nullptr));
#endif // QT_CONFIG(tooltip)
        actionCopy->setText(QCoreApplication::translate("LogManager", "Copy selected rows to clipboard", nullptr));
#if QT_CONFIG(tooltip)
        actionCopy->setToolTip(QCoreApplication::translate("LogManager", "Copy selected rows to clipboard", nullptr));
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(shortcut)
        actionCopy->setShortcut(QCoreApplication::translate("LogManager", "Ctrl+C", nullptr));
#endif // QT_CONFIG(shortcut)
        labelFilter->setText(QCoreApplication::translate("LogManager", "Filter:", nullptr));
#if QT_CONFIG(tooltip)
        editFilter->setToolTip(QCoreApplication::translate("LogManager", "Show only rows where any column to be checked contains the filter text.", nullptr));
#endif // QT_CONFIG(tooltip)
        editFilter->setPlaceholderText(QCoreApplication::translate("LogManager", "Filter text", nullptr));
        pushButton->setText(QCoreApplication::translate("LogManager", "&Close", nullptr));
        toolBar->setWindowTitle(QCoreApplication::translate("LogManager", "Log level and settings", nullptr));
    } // retranslateUi

};

namespace Ui {
    class LogManager: public Ui_LogManager {};
} // namespace Ui

QT_END_NAMESPACE

#endif // UI_LOGMANAGER_H
