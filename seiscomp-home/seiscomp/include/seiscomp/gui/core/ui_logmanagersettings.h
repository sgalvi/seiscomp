/********************************************************************************
** Form generated from reading UI file 'logmanagersettings.ui'
**
** Created by: Qt User Interface Compiler version 5.15.13
**
** WARNING! All changes made in this file will be lost when recompiling UI file!
********************************************************************************/

#ifndef UI_LOGMANAGERSETTINGS_H
#define UI_LOGMANAGERSETTINGS_H

#include <QtCore/QVariant>
#include <QtWidgets/QApplication>
#include <QtWidgets/QCheckBox>
#include <QtWidgets/QDialog>
#include <QtWidgets/QFrame>
#include <QtWidgets/QGridLayout>
#include <QtWidgets/QGroupBox>
#include <QtWidgets/QHBoxLayout>
#include <QtWidgets/QLabel>
#include <QtWidgets/QPushButton>
#include <QtWidgets/QSpacerItem>
#include <QtWidgets/QSpinBox>
#include <QtWidgets/QVBoxLayout>

QT_BEGIN_NAMESPACE

class Ui_LogManagerSettings
{
public:
    QVBoxLayout *verticalLayout_2;
    QGroupBox *groupBuffer;
    QGridLayout *gridLayout;
    QLabel *label;
    QSpinBox *spinBufferSize;
    QGroupBox *groupLogLevel;
    QVBoxLayout *vboxLayout;
    QHBoxLayout *horizontalLayout;
    QFrame *frameLogLevel;
    QSpacerItem *horizontalSpacer;
    QGroupBox *groupOptions;
    QVBoxLayout *verticalLayout;
    QCheckBox *sendOnly;
    QCheckBox *logComponent;
    QCheckBox *logContext;
    QSpacerItem *verticalSpacer;
    QHBoxLayout *hboxLayout;
    QSpacerItem *spacerItem;
    QPushButton *okButton;
    QPushButton *cancelButton;

    void setupUi(QDialog *LogManagerSettings)
    {
        if (LogManagerSettings->objectName().isEmpty())
            LogManagerSettings->setObjectName(QString::fromUtf8("LogManagerSettings"));
        LogManagerSettings->resize(403, 381);
        QSizePolicy sizePolicy(QSizePolicy::Preferred, QSizePolicy::Preferred);
        sizePolicy.setHorizontalStretch(0);
        sizePolicy.setVerticalStretch(0);
        sizePolicy.setHeightForWidth(LogManagerSettings->sizePolicy().hasHeightForWidth());
        LogManagerSettings->setSizePolicy(sizePolicy);
        verticalLayout_2 = new QVBoxLayout(LogManagerSettings);
        verticalLayout_2->setObjectName(QString::fromUtf8("verticalLayout_2"));
        groupBuffer = new QGroupBox(LogManagerSettings);
        groupBuffer->setObjectName(QString::fromUtf8("groupBuffer"));
        gridLayout = new QGridLayout(groupBuffer);
        gridLayout->setObjectName(QString::fromUtf8("gridLayout"));
        label = new QLabel(groupBuffer);
        label->setObjectName(QString::fromUtf8("label"));
        QSizePolicy sizePolicy1(QSizePolicy::Maximum, QSizePolicy::Preferred);
        sizePolicy1.setHorizontalStretch(0);
        sizePolicy1.setVerticalStretch(0);
        sizePolicy1.setHeightForWidth(label->sizePolicy().hasHeightForWidth());
        label->setSizePolicy(sizePolicy1);

        gridLayout->addWidget(label, 0, 0, 1, 1);

        spinBufferSize = new QSpinBox(groupBuffer);
        spinBufferSize->setObjectName(QString::fromUtf8("spinBufferSize"));
        spinBufferSize->setMaximum(1000000);
        spinBufferSize->setValue(1000);

        gridLayout->addWidget(spinBufferSize, 0, 1, 1, 1);


        verticalLayout_2->addWidget(groupBuffer);

        groupLogLevel = new QGroupBox(LogManagerSettings);
        groupLogLevel->setObjectName(QString::fromUtf8("groupLogLevel"));
        vboxLayout = new QVBoxLayout(groupLogLevel);
        vboxLayout->setSpacing(6);
        vboxLayout->setObjectName(QString::fromUtf8("vboxLayout"));
        vboxLayout->setContentsMargins(9, 9, 9, 9);
        horizontalLayout = new QHBoxLayout();
        horizontalLayout->setObjectName(QString::fromUtf8("horizontalLayout"));
        frameLogLevel = new QFrame(groupLogLevel);
        frameLogLevel->setObjectName(QString::fromUtf8("frameLogLevel"));
        sizePolicy.setHeightForWidth(frameLogLevel->sizePolicy().hasHeightForWidth());
        frameLogLevel->setSizePolicy(sizePolicy);
        frameLogLevel->setFrameShape(QFrame::NoFrame);
        frameLogLevel->setFrameShadow(QFrame::Raised);

        horizontalLayout->addWidget(frameLogLevel);

        horizontalSpacer = new QSpacerItem(40, 20, QSizePolicy::Expanding, QSizePolicy::Minimum);

        horizontalLayout->addItem(horizontalSpacer);


        vboxLayout->addLayout(horizontalLayout);


        verticalLayout_2->addWidget(groupLogLevel);

        groupOptions = new QGroupBox(LogManagerSettings);
        groupOptions->setObjectName(QString::fromUtf8("groupOptions"));
        verticalLayout = new QVBoxLayout(groupOptions);
        verticalLayout->setObjectName(QString::fromUtf8("verticalLayout"));
        sendOnly = new QCheckBox(groupOptions);
        sendOnly->setObjectName(QString::fromUtf8("sendOnly"));
        sendOnly->setChecked(true);

        verticalLayout->addWidget(sendOnly);

        logComponent = new QCheckBox(groupOptions);
        logComponent->setObjectName(QString::fromUtf8("logComponent"));

        verticalLayout->addWidget(logComponent);

        logContext = new QCheckBox(groupOptions);
        logContext->setObjectName(QString::fromUtf8("logContext"));
        logContext->setChecked(false);

        verticalLayout->addWidget(logContext);


        verticalLayout_2->addWidget(groupOptions);

        verticalSpacer = new QSpacerItem(20, 40, QSizePolicy::Minimum, QSizePolicy::Expanding);

        verticalLayout_2->addItem(verticalSpacer);

        hboxLayout = new QHBoxLayout();
        hboxLayout->setSpacing(6);
        hboxLayout->setObjectName(QString::fromUtf8("hboxLayout"));
        hboxLayout->setContentsMargins(0, 0, 0, 0);
        spacerItem = new QSpacerItem(131, 31, QSizePolicy::Expanding, QSizePolicy::Minimum);

        hboxLayout->addItem(spacerItem);

        okButton = new QPushButton(LogManagerSettings);
        okButton->setObjectName(QString::fromUtf8("okButton"));

        hboxLayout->addWidget(okButton);

        cancelButton = new QPushButton(LogManagerSettings);
        cancelButton->setObjectName(QString::fromUtf8("cancelButton"));

        hboxLayout->addWidget(cancelButton);


        verticalLayout_2->addLayout(hboxLayout);

        QWidget::setTabOrder(okButton, cancelButton);

        retranslateUi(LogManagerSettings);
        QObject::connect(cancelButton, SIGNAL(clicked()), LogManagerSettings, SLOT(reject()));
        QObject::connect(okButton, SIGNAL(clicked()), LogManagerSettings, SLOT(accept()));
        QObject::connect(cancelButton, SIGNAL(clicked()), LogManagerSettings, SLOT(reject()));

        QMetaObject::connectSlotsByName(LogManagerSettings);
    } // setupUi

    void retranslateUi(QDialog *LogManagerSettings)
    {
        LogManagerSettings->setWindowTitle(QCoreApplication::translate("LogManagerSettings", "System log settings", nullptr));
        groupBuffer->setTitle(QCoreApplication::translate("LogManagerSettings", "Buffer", nullptr));
        label->setText(QCoreApplication::translate("LogManagerSettings", "Lines:", nullptr));
        spinBufferSize->setSpecialValueText(QCoreApplication::translate("LogManagerSettings", "Unlimited", nullptr));
        groupLogLevel->setTitle(QCoreApplication::translate("LogManagerSettings", "Subscriptions && Notifications", nullptr));
        groupOptions->setTitle(QCoreApplication::translate("LogManagerSettings", "Options", nullptr));
        sendOnly->setText(QCoreApplication::translate("LogManagerSettings", "Send only notifications if the warn level increases", nullptr));
        logComponent->setText(QCoreApplication::translate("LogManagerSettings", "Enable logging of component", nullptr));
        logContext->setText(QCoreApplication::translate("LogManagerSettings", "Enable logging of source file and line number", nullptr));
        okButton->setText(QCoreApplication::translate("LogManagerSettings", "&OK", nullptr));
        cancelButton->setText(QCoreApplication::translate("LogManagerSettings", "&Cancel", nullptr));
    } // retranslateUi

};

namespace Ui {
    class LogManagerSettings: public Ui_LogManagerSettings {};
} // namespace Ui

QT_END_NAMESPACE

#endif // UI_LOGMANAGERSETTINGS_H
