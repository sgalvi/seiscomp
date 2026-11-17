/********************************************************************************
** Form generated from reading UI file 'processmanager.ui'
**
** Created by: Qt User Interface Compiler version 5.15.13
**
** WARNING! All changes made in this file will be lost when recompiling UI file!
********************************************************************************/

#ifndef UI_PROCESSMANAGER_H
#define UI_PROCESSMANAGER_H

#include <QtCore/QVariant>
#include <QtWidgets/QApplication>
#include <QtWidgets/QFrame>
#include <QtWidgets/QHBoxLayout>
#include <QtWidgets/QHeaderView>
#include <QtWidgets/QMainWindow>
#include <QtWidgets/QPushButton>
#include <QtWidgets/QSpacerItem>
#include <QtWidgets/QSplitter>
#include <QtWidgets/QTabWidget>
#include <QtWidgets/QTableView>
#include <QtWidgets/QVBoxLayout>
#include <QtWidgets/QWidget>

QT_BEGIN_NAMESPACE

class Ui_ProcessManager
{
public:
    QWidget *centralwidget;
    QHBoxLayout *layoutMain;
    QSplitter *splitter;
    QFrame *frame;
    QVBoxLayout *layoutLeft;
    QTableView *table;
    QHBoxLayout *layoutButtons;
    QSpacerItem *spacerButtons;
    QPushButton *btnStop;
    QPushButton *btnContinue;
    QPushButton *btnTerminate;
    QPushButton *btnKill;
    QPushButton *btnRemove;
    QPushButton *btnClear;
    QTabWidget *twOutput;
    QWidget *tabStdout;
    QVBoxLayout *layoutStdout;
    QWidget *tabStderr;
    QVBoxLayout *layoutStderr;
    QWidget *tabProcessLog;
    QVBoxLayout *layoutLog;

    void setupUi(QMainWindow *ProcessManager)
    {
        if (ProcessManager->objectName().isEmpty())
            ProcessManager->setObjectName(QString::fromUtf8("ProcessManager"));
        ProcessManager->resize(1024, 768);
        centralwidget = new QWidget(ProcessManager);
        centralwidget->setObjectName(QString::fromUtf8("centralwidget"));
        layoutMain = new QHBoxLayout(centralwidget);
        layoutMain->setObjectName(QString::fromUtf8("layoutMain"));
        splitter = new QSplitter(centralwidget);
        splitter->setObjectName(QString::fromUtf8("splitter"));
        splitter->setOrientation(Qt::Orientation::Horizontal);
        frame = new QFrame(splitter);
        frame->setObjectName(QString::fromUtf8("frame"));
        frame->setFrameShape(QFrame::Shape::StyledPanel);
        frame->setFrameShadow(QFrame::Shadow::Raised);
        layoutLeft = new QVBoxLayout(frame);
        layoutLeft->setObjectName(QString::fromUtf8("layoutLeft"));
        table = new QTableView(frame);
        table->setObjectName(QString::fromUtf8("table"));

        layoutLeft->addWidget(table);

        layoutButtons = new QHBoxLayout();
        layoutButtons->setObjectName(QString::fromUtf8("layoutButtons"));
        spacerButtons = new QSpacerItem(40, 20, QSizePolicy::Expanding, QSizePolicy::Minimum);

        layoutButtons->addItem(spacerButtons);

        btnStop = new QPushButton(frame);
        btnStop->setObjectName(QString::fromUtf8("btnStop"));
        btnStop->setEnabled(false);

        layoutButtons->addWidget(btnStop);

        btnContinue = new QPushButton(frame);
        btnContinue->setObjectName(QString::fromUtf8("btnContinue"));
        btnContinue->setEnabled(false);

        layoutButtons->addWidget(btnContinue);

        btnTerminate = new QPushButton(frame);
        btnTerminate->setObjectName(QString::fromUtf8("btnTerminate"));
        btnTerminate->setEnabled(false);

        layoutButtons->addWidget(btnTerminate);

        btnKill = new QPushButton(frame);
        btnKill->setObjectName(QString::fromUtf8("btnKill"));
        btnKill->setEnabled(false);

        layoutButtons->addWidget(btnKill);

        btnRemove = new QPushButton(frame);
        btnRemove->setObjectName(QString::fromUtf8("btnRemove"));
        btnRemove->setEnabled(false);

        layoutButtons->addWidget(btnRemove);

        btnClear = new QPushButton(frame);
        btnClear->setObjectName(QString::fromUtf8("btnClear"));
        btnClear->setEnabled(false);

        layoutButtons->addWidget(btnClear);


        layoutLeft->addLayout(layoutButtons);

        splitter->addWidget(frame);
        twOutput = new QTabWidget(splitter);
        twOutput->setObjectName(QString::fromUtf8("twOutput"));
        tabStdout = new QWidget();
        tabStdout->setObjectName(QString::fromUtf8("tabStdout"));
        layoutStdout = new QVBoxLayout(tabStdout);
        layoutStdout->setObjectName(QString::fromUtf8("layoutStdout"));
        twOutput->addTab(tabStdout, QString());
        tabStderr = new QWidget();
        tabStderr->setObjectName(QString::fromUtf8("tabStderr"));
        layoutStderr = new QVBoxLayout(tabStderr);
        layoutStderr->setObjectName(QString::fromUtf8("layoutStderr"));
        twOutput->addTab(tabStderr, QString());
        tabProcessLog = new QWidget();
        tabProcessLog->setObjectName(QString::fromUtf8("tabProcessLog"));
        layoutLog = new QVBoxLayout(tabProcessLog);
        layoutLog->setObjectName(QString::fromUtf8("layoutLog"));
        twOutput->addTab(tabProcessLog, QString());
        splitter->addWidget(twOutput);

        layoutMain->addWidget(splitter);

        ProcessManager->setCentralWidget(centralwidget);

        retranslateUi(ProcessManager);

        twOutput->setCurrentIndex(2);


        QMetaObject::connectSlotsByName(ProcessManager);
    } // setupUi

    void retranslateUi(QMainWindow *ProcessManager)
    {
        ProcessManager->setWindowTitle(QCoreApplication::translate("ProcessManager", "Manage processes", nullptr));
#if QT_CONFIG(tooltip)
        btnStop->setToolTip(QCoreApplication::translate("ProcessManager", "Stop execution of selected processes by sending SIGSTOP. Execution may be continued later on.", nullptr));
#endif // QT_CONFIG(tooltip)
        btnStop->setText(QCoreApplication::translate("ProcessManager", "Stop", nullptr));
#if QT_CONFIG(tooltip)
        btnContinue->setToolTip(QCoreApplication::translate("ProcessManager", "Continue execution of selected processes by sending SIGCONT.", nullptr));
#endif // QT_CONFIG(tooltip)
        btnContinue->setText(QCoreApplication::translate("ProcessManager", "Continue", nullptr));
#if QT_CONFIG(tooltip)
        btnTerminate->setToolTip(QCoreApplication::translate("ProcessManager", "Terminate selected processes by sending SIGTERM.", nullptr));
#endif // QT_CONFIG(tooltip)
        btnTerminate->setText(QCoreApplication::translate("ProcessManager", "Terminate", nullptr));
#if QT_CONFIG(tooltip)
        btnKill->setToolTip(QCoreApplication::translate("ProcessManager", "Kill selected processes by sending SIGKILL.", nullptr));
#endif // QT_CONFIG(tooltip)
        btnKill->setText(QCoreApplication::translate("ProcessManager", "Kill", nullptr));
#if QT_CONFIG(tooltip)
        btnRemove->setToolTip(QCoreApplication::translate("ProcessManager", "Remove selected processes which have terminated.", nullptr));
#endif // QT_CONFIG(tooltip)
        btnRemove->setText(QCoreApplication::translate("ProcessManager", "Remove", nullptr));
#if QT_CONFIG(tooltip)
        btnClear->setToolTip(QCoreApplication::translate("ProcessManager", "Remove all stopped processes which have terminated.", nullptr));
#endif // QT_CONFIG(tooltip)
        btnClear->setText(QCoreApplication::translate("ProcessManager", "Clear", nullptr));
        twOutput->setTabText(twOutput->indexOf(tabStdout), QCoreApplication::translate("ProcessManager", "Stdout", nullptr));
        twOutput->setTabText(twOutput->indexOf(tabStderr), QCoreApplication::translate("ProcessManager", "Stderr", nullptr));
        twOutput->setTabText(twOutput->indexOf(tabProcessLog), QCoreApplication::translate("ProcessManager", "Process Log", nullptr));
    } // retranslateUi

};

namespace Ui {
    class ProcessManager: public Ui_ProcessManager {};
} // namespace Ui

QT_END_NAMESPACE

#endif // UI_PROCESSMANAGER_H
